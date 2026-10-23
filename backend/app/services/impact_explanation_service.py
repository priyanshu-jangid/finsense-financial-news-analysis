import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

try:
    from google import genai
except ImportError:  # pragma: no cover
    # Fallback dummy implementation for environments without google-genai
    class _DummyGenAI:
        class Client:
            def __init__(self, *args, **kwargs):
                class _Models:
                    def generate_content(self, *args, **kwargs):
                        class _Response:
                            text = "{}"
                        return _Response()
                self.models = _Models()
        class types:
            class GenerationConfig:
                def __init__(self, *args, **kwargs):
                    pass
    genai = _DummyGenAI()


from pydantic import BaseModel, Field, ValidationError, field_validator

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models for input evidence and structured output
# ---------------------------------------------------------------------------

class ArticleEvidence(BaseModel):
    """Evidence piece representing a single news article and its sentiment.

    The fields are deliberately minimal – they are sourced from the existing
    ``Article`` and ``SentimentAnalysis`` tables and are safe to expose to the
    LLM.
    """

    id: int = Field(..., description="Primary key of the article in the DB")
    title: str = Field(..., description="Article headline")
    summary: Optional[str] = Field(None, description="Short summary of the article")
    published_at: Optional[datetime] = Field(
        None, description="Timestamp when the article was originally published"
    )
    sentiment_label: str = Field(..., description="Sentiment label (positive/neutral/negative)")
    sentiment_score: float = Field(..., description="Signed sentiment score (-1 .. 1)")

    @field_validator("sentiment_label")
    def _label_allowed(cls, v: str) -> str:
        if v not in {"positive", "neutral", "negative"}:
            raise ValueError(f"Unsupported sentiment label: {v}")
        return v

    @field_validator("sentiment_score")
    def _score_range(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError("sentiment_score must be between -1.0 and 1.0")
        return v


class ImpactEvidencePayload(BaseModel):
    """Payload supplied by the backend to the explanation service.

    It contains a bounded amount of data – enough for the LLM to reason about
    change but not the full article text (which we deliberately treat as
    untrusted).
    """

    company_id: int = Field(..., description="Database ID of the company")
    company_name: Optional[str] = Field(None, description="Human readable company name")
    period_start: Optional[datetime] = Field(
        None, description="Inclusive start of the comparison period"
    )
    period_end: Optional[datetime] = Field(
        None, description="Inclusive end of the comparison period"
    )
    articles: List[ArticleEvidence] = Field(..., description="List of relevant articles")

    @field_validator("articles")
    def _non_empty(cls, v: List[ArticleEvidence]) -> List[ArticleEvidence]:
        # Allow empty list; payload validation will be handled in service function
        return v


class ImpactExplanationResponse(BaseModel):
    """Structured response expected from Gemini.

    The service will validate the model and return the parsed object.  All
    fields are required so that downstream callers have a deterministic shape.
    """

    headline: str = Field(..., description="Short explanation headline")
    observed_facts: str = Field(..., description="Plain‑language description of the observed sentiment change")
    plausible_explanations: List[str] = Field(..., description="List of plausible causes, each as a sentence")
    supporting_article_ids: List[int] = Field(..., description="IDs of articles that support the explanations")
    contradictory_evidence: List[str] = Field(default_factory=list, description="Optional list of counter‑evidence statements")
    uncertainty: str = Field(..., description="Explicit statement of uncertainty or data limitation")

    @field_validator("supporting_article_ids")
    def _id_positive(cls, v: List[int]) -> List[int]:
        # Ensure all IDs are positive integers
        for item in v:
            if item <= 0:
                raise ValueError("article IDs must be positive integers")
        return v


# ---------------------------------------------------------------------------
# Core service function
# ---------------------------------------------------------------------------

def _init_gemini_client() -> Any:
    """Initialize a google-genai Client with API key and timeout.

    Validates the API key, configures the SDK, and returns a client instance.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.error("Gemini API key not configured in Settings")
        raise RuntimeError("Gemini API key is missing")
    try:
        genai.configure(api_key=api_key)
    except Exception as exc:
        logger.error("Failed to configure Gemini SDK: %s", exc)
        raise RuntimeError("Gemini SDK configuration failed") from exc
    timeout_sec = getattr(settings, "GEMINI_REQUEST_TIMEOUT_SECONDS", 30)
    client = genai.Client(api_key=api_key, timeout=timeout_sec)
    return client


def _build_prompt(evidence: ImpactEvidencePayload) -> str:
    """Create a concise, safety‑focused prompt for Gemini.

    The prompt includes only the fields that are safe to share – no raw article
    content, no user data, and no secrets.  It explicitly asks the model to:
    * Return **JSON** matching ``ImpactExplanationResponse``
    * Not claim causation, not predict returns, and to be explicit about
      uncertainty.
    """
    # Summarise article evidence without the full text.
    article_summaries = []
    for art in evidence.articles:
        parts = [f"ID: {art.id}", f"Title: {art.title}"]
        if art.summary:
            parts.append(f"Summary: {art.summary}")
        if art.published_at:
            parts.append(f"Published: {art.published_at.isoformat()}")
        parts.append(f"Sentiment: {art.sentiment_label} (score={art.sentiment_score})")
        article_summaries.append(" | ".join(parts))

    article_block = "\n".join(article_summaries)

    period = (
        f"Period: {evidence.period_start.isoformat()} to {evidence.period_end.isoformat()}"
        if evidence.period_start and evidence.period_end
        else "Period: not provided"
    )

    company = evidence.company_name or f"Company ID {evidence.company_id}"

    prompt = (
        "You are a financial‑news analysis assistant. Using the provided evidence,"
        " generate a concise impact explanation. **Return ONLY valid JSON** that"
        " conforms to the following schema (field names and types are exact):\n"
        f"{json.dumps(ImpactExplanationResponse.model_json_schema(), indent=2)}\n\n"
        "Guidelines:\n"
        "- Do NOT claim that the news caused the sentiment change – only suggest"
        " plausible explanations.\n"
        "- Do NOT predict stock returns or financial performance.\n"
        "- If any citation ID is not present in the supplied evidence, ignore it.\n"
        "- Include an explicit uncertainty statement.\n"
        "- Use the article IDs from the evidence for any supporting citations.\n\n"
        f"Company: {company}\n"
        f"{period}\n"
        "Articles (one per line):\n"
        f"{article_block}\n"
    )
    return prompt






# Removed legacy compatibility wrapper; _init_gemini_client is defined earlier.


def _call_gemini(client, prompt: str) -> str:
    """Execute the Gemini request.

    The ``client`` may be a ``GenerativeModel`` (real SDK) or a mock object used
    in tests that provides ``models.generate_content``. The function sends the
    prompt and returns the raw response text, raising ``RuntimeError`` on any
    SDK error.
    """
    try:
        # Both real client and mock client should expose a models.generate_content method
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json"
            ),
        )
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini request failed: %s", str(exc))
        raise RuntimeError("Gemini request failed") from exc


def explain_impact(evidence_dict: Dict[str, Any]) -> ImpactExplanationResponse:
    """Public API used by the test suite.

    1. Validate the incoming payload against ``ImpactEvidencePayload``.
    2. Initialise the Gemini model (or a mocked client in tests).
    3. Build a safe prompt.
    4. Call Gemini and parse the JSON response.
    5. Validate the response against ``ImpactExplanationResponse``.
    6. Filter ``supporting_article_ids`` to IDs present in the evidence.
    """
    # 1. Payload validation
    try:
        payload = ImpactEvidencePayload.model_validate(evidence_dict)
    except ValidationError as ve:
        logger.error("Invalid impact evidence payload: %s", ve)
        raise ValueError("Invalid impact evidence payload") from ve

    # Ensure at least one article is present; this validation is purposefully in the service
    if not payload.articles:
        logger.error("Invalid impact evidence payload: no articles provided")
        raise ValueError("Invalid impact evidence payload")
    # 2. Initialise model/client
    client = _init_gemini_client()

    # 3. Build prompt
    prompt = _build_prompt(payload)

    # 4. Call Gemini
    raw_response = _call_gemini(client, prompt)

    # 5. Parse JSON
    try:
        response_json = json.loads(raw_response)
    except json.JSONDecodeError as jde:
        logger.error("Malformed JSON from Gemini: %s", raw_response)
        raise RuntimeError("malformed JSON") from jde

    # 6. Validate response schema
    try:
        response_obj = ImpactExplanationResponse.model_validate(response_json)
    except ValidationError as ve:
        logger.error("Response validation failed: %s", ve)
        raise RuntimeError("response validation failed") from ve

    # 7. Filter supporting_article_ids to those actually present in the evidence
    provided_ids = {article.id for article in payload.articles}
    filtered_ids = [aid for aid in response_obj.supporting_article_ids if aid in provided_ids]
    response_obj.supporting_article_ids = filtered_ids

    return response_obj

# ---------------------------------------------------------------------------
# End of service module
# ---------------------------------------------------------------------------
