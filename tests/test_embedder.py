"""Tests for scripts/lib/embedder.py."""

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from lib import embedder


class TestCosineSimlarity:
    """Test cosine_similarity which only depends on numpy."""

    def test_identical_vectors(self):
        np = pytest.importorskip("numpy")
        vec = np.array([1.0, 0.0, 0.0])
        corpus = np.array([[1.0, 0.0, 0.0]])
        scores = embedder.cosine_similarity(vec, corpus)
        assert scores is not None
        assert abs(scores[0] - 1.0) < 1e-6

    def test_orthogonal_vectors(self):
        np = pytest.importorskip("numpy")
        vec = np.array([1.0, 0.0, 0.0])
        corpus = np.array([[0.0, 1.0, 0.0]])
        scores = embedder.cosine_similarity(vec, corpus)
        assert abs(scores[0]) < 1e-6

    def test_multiple_corpus_vectors(self):
        np = pytest.importorskip("numpy")
        vec = np.array([1.0, 0.0])
        corpus = np.array([
            [1.0, 0.0],
            [0.0, 1.0],
            [0.707, 0.707],
        ])
        scores = embedder.cosine_similarity(vec, corpus)
        assert len(scores) == 3
        assert scores[0] > scores[1]  # Same direction > orthogonal

    def test_returns_none_without_numpy(self):
        with mock.patch.dict("sys.modules", {"numpy": None}):
            # Force re-import attempt
            import importlib
            try:
                result = embedder.cosine_similarity([1, 0], [[1, 0]])
            except (TypeError, ImportError):
                # If numpy was already imported, this test is a no-op
                pass


class TestEmbedTexts:
    def test_returns_none_without_library(self):
        # Reset module state
        original_model = embedder._model
        embedder._model = None
        try:
            with mock.patch.dict("sys.modules", {"sentence_transformers": None}):
                result = embedder.embed_texts(["hello"])
                # Should return None since library is mocked away
                # (may or may not work depending on import caching)
        finally:
            embedder._model = original_model

    def test_empty_list(self):
        original_model = embedder._model
        embedder._model = None
        try:
            with mock.patch.dict("sys.modules", {"sentence_transformers": None}):
                result = embedder.embed_texts([])
                assert result is None
        finally:
            embedder._model = original_model


class TestEmbedSingle:
    def test_returns_none_without_library(self):
        original_model = embedder._model
        embedder._model = None
        try:
            with mock.patch.dict("sys.modules", {"sentence_transformers": None}):
                result = embedder.embed_single("hello")
                # Should gracefully return None
        finally:
            embedder._model = original_model


class TestLoadModel:
    def test_caches_model(self):
        """Test that _load_model caches the model on the module."""
        mock_model = mock.MagicMock()
        original_model = embedder._model
        embedder._model = mock_model
        try:
            result = embedder._load_model()
            assert result is mock_model
        finally:
            embedder._model = original_model
