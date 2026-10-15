"""Company-article matching engine for financial news.

Correlates news articles to tracked companies using:
1. Provider-supplied entity symbols and names (primary).
2. Headline / title keyword and symbol matching (primary).
3. Description / summary fallback matching (secondary).
4. Guardrails to prevent false positives from short/common tickers.
"""

from dataclasses import dataclass
import re
from typing import Any

from shared.models import Company

# Common English words that can coincide with stock tickers.
AMBIGUOUS_TICKERS = {
    "A", "ALL", "AM", "AN", "AND", "AS", "AT", "BE", "CAN", "DO",
    "FOR", "GO", "HE", "IF", "IN", "IS", "IT", "ME", "MY", "NO",
    "NOT", "OF", "ON", "OR", "SO", "TO", "UP", "US", "WE", "STRING",
}


@dataclass
class MatchResult:
    company: Company
    relevance_score: float
    is_primary: bool
    match_source: str  # 'provider_entity', 'title_name', 'title_ticker', 'body_name', 'body_ticker'


def _normalize_ticker(symbol: str) -> str:
    """Normalize exchange-qualified tickers like CANBK.NS or RELIANCE.BO to CANBK or RELIANCE."""
    clean = symbol.strip().upper()
    if "." in clean:
        clean = clean.split(".")[0]
    return clean


def match_companies_for_article(
    raw_article: dict[str, Any],
    companies: list[Company],
) -> list[MatchResult]:
    """Identify which tracked companies genuinely relate to the given article."""
    if not companies:
        return []

    title = (raw_article.get("title") or "").strip()
    description = (raw_article.get("description") or raw_article.get("snippet") or "").strip()
    provider_entities = raw_article.get("entities") or []

    # Map companies for quick lookup
    ticker_to_company: dict[str, Company] = {c.ticker.upper(): c for c in companies}
    name_to_company: dict[str, Company] = {c.name.strip().lower(): c for c in companies}

    matched: dict[int, MatchResult] = {}

    # 1. Provider-supplied structured entities (highest confidence)
    for entity in provider_entities:
        if not isinstance(entity, dict):
            continue

        raw_sym = (entity.get("symbol") or "").strip().upper()
        norm_sym = _normalize_ticker(raw_sym)
        ent_name = (entity.get("name") or "").strip().lower()

        matched_company = ticker_to_company.get(raw_sym) or ticker_to_company.get(norm_sym) or name_to_company.get(ent_name)

        if matched_company and matched_company.id not in matched:
            raw_match_score = entity.get("match_score")
            score = 0.95
            if isinstance(raw_match_score, (int, float)):
                # Normalize provider match score (e.g. 20-100) to range 0.8 - 1.0
                score = min(1.0, max(0.8, raw_match_score / 100.0 if raw_match_score > 1.0 else raw_match_score))

            matched[matched_company.id] = MatchResult(
                company=matched_company,
                relevance_score=round(score, 2),
                is_primary=True,
                match_source="provider_entity",
            )

    # 2. Headline / Title matching
    for company in companies:
        if company.id in matched:
            continue

        c_name = company.name.strip()
        c_ticker = company.ticker.strip().upper()

        # Company name in title (whole word, case-insensitive)
        if len(c_name) >= 3:
            name_pattern = rf"\b{re.escape(c_name)}\b"
            if re.search(name_pattern, title, re.IGNORECASE):
                matched[company.id] = MatchResult(
                    company=company,
                    relevance_score=0.88,
                    is_primary=True,
                    match_source="title_name",
                )
                continue

        # Company ticker in title
        if c_ticker in AMBIGUOUS_TICKERS or len(c_ticker) <= 3:
            # Ambiguous/short tickers require cashtag ($TICKER) or exchange prefix (e.g. NSE: TICKER)
            strict_pattern = rf"(?:\$|NSE:\s*|BSE:\s*|NASDAQ:\s*|NYSE:\s*)\b{re.escape(c_ticker)}\b"
            if re.search(strict_pattern, title, re.IGNORECASE):
                matched[company.id] = MatchResult(
                    company=company,
                    relevance_score=0.82,
                    is_primary=True,
                    match_source="title_ticker_strict",
                )
        else:
            # Long, unambiguous ticker in title (must be uppercase)
            ticker_pattern = rf"\b{re.escape(c_ticker)}\b"
            if re.search(ticker_pattern, title):
                matched[company.id] = MatchResult(
                    company=company,
                    relevance_score=0.80,
                    is_primary=True,
                    match_source="title_ticker",
                )

    # 3. Description / Summary fallback matching (secondary relevance)
    for company in companies:
        if company.id in matched:
            continue

        c_name = company.name.strip()
        c_ticker = company.ticker.strip().upper()

        if len(c_name) >= 3:
            name_pattern = rf"\b{re.escape(c_name)}\b"
            if re.search(name_pattern, description, re.IGNORECASE):
                matched[company.id] = MatchResult(
                    company=company,
                    relevance_score=0.65,
                    is_primary=False,
                    match_source="body_name",
                )
                continue

        # Strict ticker in description
        strict_pattern = rf"(?:\$|NSE:\s*|BSE:\s*|NASDAQ:\s*|NYSE:\s*)\b{re.escape(c_ticker)}\b"
        if re.search(strict_pattern, description, re.IGNORECASE):
            matched[company.id] = MatchResult(
                company=company,
                relevance_score=0.60,
                is_primary=False,
                match_source="body_ticker_strict",
            )

    return list(matched.values())
