import json

import pytest
from fastapi.testclient import TestClient

from app.llm import LLMError
from app.main import app, get_answer_service
from app.rag import AnswerService, AskInput, Draft, Verification
from app.retrieval import IndexUnavailable, SearchHit, SearchOutput

TEXT = "Fixture técnica: a taxa hipotética de teste é 0,1% no ano de 2026. Não é legislação."
QUOTE = "a taxa hipotética de teste é 0,1% no ano de 2026"


class FixtureRetriever:
    def __init__(self, empty=False):
        self.empty = empty

    def search(self, question, top_k):
        return SearchOutput(
            question=question, results=[] if self.empty else [SearchHit(
                chunk_id="fixture:1", document_id="fixture-doc", source_id="fixture",
                section="Fixture", score=0.99, text=TEXT, title="Fixture sem validade jurídica",
                url="https://www.gov.br/fixture", accessed_at="2026-11-11T00:00:00Z",
                temporal_scope="Teste", legal_validity="Fixture técnica", start_char=100, end_char=100 + len(TEXT),
            )], model_id="fixture", model_revision="fixture", index_generation="fixture", latency_ms=0,
        )


def draft(text="A taxa hipotética de teste é 0,1% no ano de 2026.", quote=QUOTE, chunk_id="fixture:1"):
    return {"decision": "answer", "claims": [{"text": text, "evidence": [{"chunk_id": chunk_id, "quote": quote}]}]}


class FixtureLLM:
    """Saídas controladas para testar regras; não avalia um LLM real."""
    provider, model = "fixture", "fixture"

    def __init__(self, generation=None, verification=None):
        self.generation = generation or draft()
        self.verification = verification or {"answers_question": True, "checks": [{"claim_index": 0, "supported": True}]}
        self.calls = []

    def complete(self, system, payload, schema):
        self.calls.append((system, payload, schema))
        return schema.model_validate(self.generation if schema is Draft else self.verification)


def ask(llm=None, retriever=None, question="Qual é a taxa hipotética da fixture?"):
    return AnswerService(retriever or FixtureRetriever(), llm or FixtureLLM()).ask(AskInput(question=question))


def test_answer_has_server_owned_sources_and_exact_quote_offsets():
    llm = FixtureLLM()
    result = ask(llm)
    assert result.status == "answered" and "[1]" in result.answer
    citation = result.citations[0]
    assert citation.url == "https://www.gov.br/fixture"
    assert citation.title == "Fixture sem validade jurídica"
    assert TEXT[citation.start_char - 100:citation.end_char - 100] == citation.quote
    assert result.claims[0].citation_ids == [1]
    assert len(llm.calls) == 2 and llm.calls[1][2] is Verification
    assert llm.calls[1][1]["question"] == result.question


@pytest.mark.parametrize("generation", [
    draft(chunk_id="invented"), draft(quote="Trecho inventado e ausente da fixture"),
    draft(text="A taxa hipotética é 1% em 2026."),
    draft(text="A taxa hipotética é 0,1 no ano de 2026."),
    draft(text="Consulte https://invented.example"), draft(text="Taxa hipotética [99]"),
])
def test_invalid_quote_reference_number_or_link_abstains(generation):
    llm = FixtureLLM(generation)
    result = ask(llm)
    assert result.status == "abstained" and result.reason == "invalid_evidence"
    assert not result.citations and not result.claims
    assert "invented" not in result.answer
    assert len(llm.calls) == 1


@pytest.mark.parametrize("verification", [
    {"answers_question": False, "checks": [{"claim_index": 0, "supported": True}]},
    {"answers_question": True, "checks": [{"claim_index": 0, "supported": False}]},
    {"answers_question": True, "checks": []},
    {"answers_question": True, "checks": [{"claim_index": 1, "supported": True}]},
    {"answers_question": True, "checks": [{"claim_index": 0, "supported": True}, {"claim_index": 0, "supported": True}]},
])
def test_semantic_rejection_or_incomplete_review_abstains(verification):
    result = ask(FixtureLLM(verification=verification))
    assert result.status == "abstained" and result.reason == "unsupported_claims"
    assert not result.citations and not result.claims


def test_empty_retrieval_skips_provider():
    llm = FixtureLLM()
    assert ask(llm, FixtureRetriever(empty=True)).reason == "no_evidence"
    assert not llm.calls


def test_model_abstention_despite_high_similarity():
    llm = FixtureLLM({"decision": "abstain", "claims": []})
    result = ask(llm, question="Qual é a capital do Japão?")
    assert result.status == "abstained" and result.reason == "insufficient_evidence"
    assert len(llm.calls) == 1


def test_reuses_citation_for_multiple_claims():
    generation = draft()
    generation["claims"] *= 2
    checks = {"answers_question": True, "checks": [
        {"claim_index": index, "supported": True} for index in range(2)
    ]}
    result = ask(FixtureLLM(generation, checks))
    assert len(result.citations) == 1
    assert [claim.citation_ids for claim in result.claims] == [[1], [1]]


def test_api_contract_and_input_validation():
    app.dependency_overrides[get_answer_service] = lambda: AnswerService(FixtureRetriever(), FixtureLLM())
    try:
        client = TestClient(app)
        assert client.post("/ask", json={"question": "Pergunta da fixture"}).json()["status"] == "answered"
        for payload in [
            {"question": "aa"}, {"question": " "}, {"question": "a" * 501},
            {"question": "fixture", "top_k": 6}, {"question": "fixture", "top_k": True},
            {"question": "fixture", "url": "https://invented.example"},
        ]:
            assert client.post("/ask", json=payload).status_code == 422
        assert "/ask" in client.get("/openapi.json").json()["paths"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("error,status", [(LLMError("Falha controlada", 429), 429), (IndexUnavailable("Fixture"), 503)])
def test_api_keeps_operational_errors_distinct_from_abstention(error, status):
    class BrokenService:
        def ask(self, request):
            raise error

    app.dependency_overrides[get_answer_service] = BrokenService
    try:
        response = TestClient(app).post("/ask", json={"question": "Pergunta de teste"})
        assert response.status_code == status
        assert "answer" not in response.json()
    finally:
        app.dependency_overrides.clear()
