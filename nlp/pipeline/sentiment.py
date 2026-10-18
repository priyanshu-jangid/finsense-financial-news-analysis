'''Sentiment analysis pipeline for FinSense.

This module provides a lightweight, reusable SentimentEngine class that can be
instantiated once and reused across the application. The engine attempts to
load a pretrained transformer model (default: ``ProsusAI/finbert``) suitable for
financial text. If the required ``transformers`` library is not installed or the
model cannot be loaded, a clear ``RuntimeError`` is raised.

The public ``analyze`` method accepts raw article text and returns a dictionary
containing:

* ``label`` – one of ``positive``, ``neutral`` or ``negative``.
* ``score`` – signed sentiment score in the range ``-1.0`` to ``1.0``.
* ``confidence`` – model confidence in the range ``0.0`` to ``1.0``.
* ``model_used`` – identifier of the underlying model.

The implementation is deliberately minimal to keep dependencies light. The
class separates model loading from inference so the heavyweight model is only
loaded once during application start‑up. Unit tests mock the private ``_pipeline``
attribute, allowing deterministic testing without internet access or model
weights.
''' 

from __future__ import annotations

import os
from typing import Any, Dict

# ``transformers`` is an optional dependency. Import lazily so that the
# package can be used in environments where it is not installed (e.g. during
# unit tests that mock the pipeline).
try:
    from transformers import pipeline  # type: ignore
except ImportError:  # pragma: no cover
    pipeline = None  # type: ignore


class SentimentEngine:
    """Encapsulates a sentiment analysis model.

    Parameters
    ----------
    model_name: str, optional
        HuggingFace model identifier. The default ``ProsusAI/finbert`` is a
        lightweight, finance‑oriented BERT model that provides the three
        required sentiment labels.
    """

    def __init__(self, model_name: str | None = None) -> None:
        # Resolve the model name from an environment variable if present –
        # this makes the engine configurable without code changes.
        env_name = os.getenv("FINBERT_MODEL_NAME")
        self.model_name: str = model_name or env_name or "ProsusAI/finbert"
        self._pipeline = None  # Lazy load on first analysis
        self.model_used: str = self.model_name

    def _load_pipeline(self):
        """Create a ``transformers`` text‑classification pipeline.

        Returns the pipeline object or raises ``RuntimeError`` with a helpful
        message if the ``transformers`` library is missing or the model cannot be
        downloaded.
        """
        if pipeline is None:  # pragma: no cover
            raise RuntimeError(
                "The 'transformers' library is required for SentimentEngine but is"
                " not installed. Install it via 'pip install transformers' and"
                " ensure appropriate model files are available."
            )
        try:
            # ``pipeline`` will lazily download the model weights on first use.
            # For environments without internet access (e.g., CI) the caller can
            # mock the resulting object, so we only attempt to instantiate it
            # here.
            return pipeline("sentiment-analysis", model=self.model_name)
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                f"Failed to load sentiment model '{self.model_name}': {exc}"
            ) from exc

    def analyze(self, text: str) -> Dict[str, Any]:
        """Run sentiment analysis on *text*.

        The underlying transformer model returns a list of dictionaries, each
        containing a ``label`` and a ``score``.  We select the entry with the
        highest score as the prediction.  The signed ``score`` follows the rule:

        * ``positive`` → ``+score``
        * ``negative`` → ``-score``
        * ``neutral``  → ``0.0`` (the raw score is ignored for neutrality)

        ``confidence`` is the raw probability of the chosen label (the maximum
        score).  ``model_used`` mirrors the model identifier supplied at
        construction.

        Empty or whitespace‑only input is treated as neutral with zero confidence.
        """
        if not isinstance(text, str):
            raise ValueError("Input text must be a string")
        cleaned = text.strip()
        if not cleaned:
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model_used": self.model_used,
            }

        # ``self._pipeline`` returns a list like:
        #   [{"label": "POSITIVE", "score": 0.97}, ...]
        try:
            # Lazy load the pipeline on first call if not already loaded
            if self._pipeline is None:
                self._pipeline = self._load_pipeline()
            raw_outputs = self._pipeline(cleaned)
        except Exception as exc:  # pragma: no cover
            # Propagate as a RuntimeError so callers can differentiate model
            # failures from other errors.
            raise RuntimeError(f"Sentiment inference failed: {exc}") from exc

        # Normalise to a list (some pipelines return a single dict).
        if isinstance(raw_outputs, dict):
            raw_outputs = [raw_outputs]
        if not raw_outputs:
            # Defensive fallback – should not happen with a well‑behaved model.
            return {
                "label": "neutral",
                "score": 0.0,
                "confidence": 0.0,
                "model_used": self.model_used,
            }

        # Pick the entry with the highest confidence.
        best = max(raw_outputs, key=lambda r: r.get("score", 0))
        raw_label = str(best.get("label", "NEUTRAL")).lower()
        raw_score = float(best.get("score", 0.0))
        raw_confidence = float(best.get("confidence", raw_score))
        model_used = best.get("model_used", self.model_used)
        # Validate output fields
        if raw_label not in {"positive", "negative", "neutral"}:
            raise ValueError(f"Unexpected sentiment label: {raw_label}")
        if not (0.0 <= raw_score <= 1.0):
            raise ValueError(f"Score out of bounds: {raw_score}")
        if not (0.0 <= raw_confidence <= 1.0):
            raise ValueError(f"Confidence out of bounds: {raw_confidence}")
        if not isinstance(model_used, str) or not model_used:
            raise ValueError("model_used must be a non-empty string")
        # Map possible variant labels to the three canonical ones.
        if "positive" in raw_label:
            label = "positive"
            signed_score = min(max(raw_score, 0.0), 1.0)
        elif "negative" in raw_label:
            label = "negative"
            signed_score = -min(max(raw_score, 0.0), 1.0)
        else:
            label = "neutral"
            signed_score = 0.0

        confidence = min(max(raw_confidence, 0.0), 1.0)

        return {
            "label": label,
            "score": signed_score,
            "confidence": confidence,
            "model_used": model_used,
        }

    # The following method is for testing purposes – it allows injection of a
    # mock pipeline without relying on internal attributes.
    def _set_pipeline(self, pipeline_obj) -> None:  # pragma: no cover
        """Replace the internal pipeline with *pipeline_obj*.

        Used by unit tests to avoid downloading large model weights.
        """
        self._pipeline = pipeline_obj
