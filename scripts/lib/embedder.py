"""Embedding abstraction for ContextForge.

Provides lazy-loaded sentence-transformer embeddings and a cosine
similarity helper. All functions degrade gracefully when the
sentence-transformers library is not installed, returning None
instead of raising.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Module-level model cache
_model = None


def _detect_device() -> str:
    """Detect the best available compute device for embeddings.

    Checks for CUDA (NVIDIA GPU) and MPS (Apple Silicon) via torch,
    falling back to CPU if neither is available or torch is not installed.
    """
    try:
        import torch
    except ImportError:
        return "cpu"

    try:
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass

    return "cpu"


def _load_model(config: Optional[Dict[str, Any]] = None):
    """Lazy-load the SentenceTransformer model.

    Uses ``all-MiniLM-L6-v2`` by default on the best available device
    (CUDA > MPS > CPU), with the model cache stored in
    ``{data_dir}/models/``.

    Args:
        config: Optional configuration dict. Supports keys under
            ``"embedding"`` such as ``model``, ``device``, and
            under the top level, ``data_dir`` for cache location.

    Returns:
        A SentenceTransformer model instance, or None if the library
        is not installed.
    """
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.debug(
            "sentence-transformers is not installed — "
            "embedding features disabled."
        )
        return None

    model_name = "all-MiniLM-L6-v2"
    device = _detect_device()
    cache_folder = None

    if config:
        embedding_config = config.get("embedding", {})
        model_name = embedding_config.get("model", model_name)
        configured_device = embedding_config.get("device")
        if configured_device and configured_device != "auto":
            device = configured_device

        data_dir = config.get("data_dir")
        if data_dir:
            cache_folder = str(Path(data_dir) / "models")

    try:
        kwargs: Dict[str, Any] = {"device": device}
        if cache_folder:
            kwargs["cache_folder"] = cache_folder
        _model = SentenceTransformer(model_name, **kwargs)
        logger.info(
            "Loaded embedding model %s on %s", model_name, device
        )
        return _model
    except Exception as exc:
        logger.error("Failed to load embedding model %s: %s", model_name, exc)
        return None


def embed_texts(
    texts: List[str], config: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """Compute embeddings for a batch of texts.

    Args:
        texts: List of text strings to embed.
        config: Optional configuration dict passed to ``_load_model``.

    Returns:
        A numpy array of shape ``(len(texts), embedding_dim)`` with
        normalized vectors, or None if embedding is unavailable.
    """
    model = _load_model(config)
    if model is None:
        return None

    if not texts:
        logger.debug("embed_texts called with empty list")
        return None

    try:
        embeddings = model.encode(texts, normalize_embeddings=True)
        logger.debug("Embedded %d texts", len(texts))
        return embeddings
    except Exception as exc:
        logger.error("Embedding failed for %d texts: %s", len(texts), exc)
        return None


def embed_single(
    text: str, config: Optional[Dict[str, Any]] = None
) -> Optional[Any]:
    """Compute the embedding for a single text string.

    Args:
        text: The text to embed.
        config: Optional configuration dict passed to ``_load_model``.

    Returns:
        A 1D numpy array of length ``embedding_dim`` with a normalized
        vector, or None if embedding is unavailable.
    """
    model = _load_model(config)
    if model is None:
        return None

    try:
        embedding = model.encode(text, normalize_embeddings=True)
        logger.debug("Embedded single text (%d chars)", len(text))
        return embedding
    except Exception as exc:
        logger.error("Single embedding failed: %s", exc)
        return None


def cosine_similarity(query_vec, corpus_vecs):
    """Compute cosine similarity between a query vector and corpus vectors.

    Since sentence-transformers produces normalized vectors, cosine
    similarity is equivalent to the dot product.

    Args:
        query_vec: A 1D numpy array (the query embedding).
        corpus_vecs: A 2D numpy array of shape ``(n, dim)`` (corpus
            embeddings).

    Returns:
        A 1D numpy array of similarity scores of length ``n``, or
        None if numpy is not available.
    """
    try:
        import numpy as np
    except ImportError:
        logger.debug("numpy is not installed — cannot compute similarity.")
        return None

    query_vec = np.asarray(query_vec)
    corpus_vecs = np.asarray(corpus_vecs)

    # Dot product for pre-normalized vectors equals cosine similarity
    scores = np.dot(corpus_vecs, query_vec)
    return scores
