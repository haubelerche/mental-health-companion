"""Tests for counseling_retriever and its integration with Friend agent injection logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# counseling_retriever unit tests
# ---------------------------------------------------------------------------


def _make_row(question: str, response: str, similarity: float):
    row = MagicMock()
    row.question = question
    row.response = response
    row.similarity = similarity
    return row


class TestGetSimilarCounselingExamples:
    def _call(self, user_message="I feel hopeless", api_key="sk-test", **kwargs):
        from app.services.counseling_retriever import get_similar_counseling_examples

        return get_similar_counseling_examples(user_message, api_key=api_key, **kwargs)

    def _patch_db(self, dialect: str, rows: list):
        mock_engine = MagicMock()
        mock_engine.dialect.name = dialect
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = rows
        mock_factory = MagicMock(return_value=mock_db)
        mock_embed_resp = MagicMock()
        mock_embed_resp.data = [MagicMock(embedding=[0.1] * 1536)]
        return mock_engine, mock_factory, mock_embed_resp

    def test_happy_path_returns_examples_above_threshold(self):
        mock_row = _make_row("I feel hopeless", "That sounds really hard.", 0.82)
        mock_engine, mock_factory, mock_embed_resp = self._patch_db("postgresql", [mock_row])

        with (
            patch("app.db.session.get_engine", return_value=mock_engine),
            patch("app.db.session.get_session_factory", return_value=mock_factory),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.embeddings.create.return_value = mock_embed_resp
            result = self._call()

        assert len(result) == 1
        assert result[0]["instruction"] == "I feel hopeless"
        assert result[0]["response"] == "That sounds really hard."

    def test_below_similarity_threshold_returns_empty(self):
        mock_row = _make_row("Unrelated topic", "Some response.", 0.50)
        mock_engine, mock_factory, mock_embed_resp = self._patch_db("postgresql", [mock_row])

        with (
            patch("app.db.session.get_engine", return_value=mock_engine),
            patch("app.db.session.get_session_factory", return_value=mock_factory),
            patch("openai.OpenAI") as mock_openai,
        ):
            mock_openai.return_value.embeddings.create.return_value = mock_embed_resp
            result = self._call()

        assert result == []

    def test_non_postgresql_returns_empty(self):
        mock_engine = MagicMock()
        mock_engine.dialect.name = "sqlite"

        with patch("app.db.session.get_engine", return_value=mock_engine):
            result = self._call()

        assert result == []

    def test_empty_message_returns_empty(self):
        result = self._call(user_message="   ")
        assert result == []

    def test_missing_api_key_returns_empty(self):
        result = self._call(api_key="")
        assert result == []

    def test_exception_returns_empty_silently(self):
        mock_engine = MagicMock()
        mock_engine.dialect.name = "postgresql"

        with (
            patch("app.db.session.get_engine", return_value=mock_engine),
            patch("openai.OpenAI", side_effect=RuntimeError("network error")),
        ):
            result = self._call()

        assert result == []


# ---------------------------------------------------------------------------
# _build_mentalchat_examples injection logic tests
# ---------------------------------------------------------------------------


class TestBuildMentalchatExamples:
    def _call(self, user_message="I feel hopeless", api_key="sk-test", distress_score=0.5):
        from app.services.langgraph_chat import _build_mentalchat_examples

        return _build_mentalchat_examples(user_message, api_key, distress_score=distress_score)

    def test_sos_path_not_called_directly(self):
        # _build_mentalchat_examples is never called on SOS path (SOS is handled before LangGraph).
        # Verify: distress < 0.42 returns empty (quick path guard).
        result = self._call(distress_score=0.30)
        assert result == ""

    def test_low_distress_returns_empty(self):
        result = self._call(distress_score=0.41)
        assert result == ""

    def test_distress_at_threshold_tries_retriever(self):
        with patch(
            "app.services.counseling_retriever.get_similar_counseling_examples",
            return_value=[],
        ) as mock_fn:
            mock_retriever = MagicMock()
            mock_retriever.is_ready = False
            with patch("app.services.mental_chat_retriever.MentalChatRetriever") as mock_cls:
                mock_cls.instance.return_value = mock_retriever
                result = self._call(distress_score=0.42)
        mock_fn.assert_called_once()
        assert result == ""

    def test_high_distress_requests_top_3(self):
        example = {"instruction": "Q", "response": "A"}

        def _fake_retriever(msg, *, api_key, top_k, min_similarity):
            return [example] * top_k

        with patch(
            "app.services.counseling_retriever.get_similar_counseling_examples",
            side_effect=_fake_retriever,
        ) as mock_fn:
            result = self._call(distress_score=0.72)

        _, kwargs = mock_fn.call_args
        assert kwargs.get("top_k") == 3
        assert "Ví dụ tham khảo" in result

    def test_medium_distress_requests_top_2(self):
        example = {"instruction": "Q", "response": "A"}

        def _fake_retriever(msg, *, api_key, top_k, min_similarity):
            return [example] * top_k

        with patch(
            "app.services.counseling_retriever.get_similar_counseling_examples",
            side_effect=_fake_retriever,
        ) as mock_fn:
            result = self._call(distress_score=0.55)

        _, kwargs = mock_fn.call_args
        assert kwargs.get("top_k") == 2

    def test_fallback_to_mentalchat_retriever_when_supabase_empty(self):
        example = {"instruction": "fallback Q", "response": "fallback A"}
        mock_retriever = MagicMock()
        mock_retriever.is_ready = True
        mock_retriever.search.return_value = [example]

        with (
            patch(
                "app.services.counseling_retriever.get_similar_counseling_examples",
                return_value=[],
            ),
            patch("app.services.mental_chat_retriever.MentalChatRetriever") as mock_cls,
        ):
            mock_cls.instance.return_value = mock_retriever
            result = self._call(distress_score=0.50)

        assert "fallback Q" in result
