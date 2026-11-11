import hashlib
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.chunking import prepare_chunks, sections
from app.embeddings import mean_pool, model_spec
from app.main import app, get_retriever
from app.retrieval import IndexUnavailable, Retriever, build_index, load_bundle


class FixtureEncoder:
    """Vetores controlados para contratos; não substituem avaliação do modelo real."""

    def encode(self, texts, kind):
        result = np.zeros((len(texts), model_spec()["dimensions"]), dtype=np.float32)
        for index, text in enumerate(texts):
            result[index, 1 if "beta" in text else 0] = 1
        return result


@pytest.fixture
def bundle(tmp_path):
    documents = []
    for name in ["alpha", "beta"]:
        text = f"Fixture técnica {name}; sem conteúdo jurídico."
        digest = hashlib.sha256(text.encode()).hexdigest()
        documents.append({
            "id": name, "document_id": f"{name}:{digest[:16]}", "text": text,
            "text_sha256": digest, "title": f"Fixture {name}",
            "url": f"https://www.gov.br/fixture-{name}",
            "accessed_at": "2026-11-11T00:00:00+00:00", "temporal_scope": "Teste",
            "legal_validity": "Fixture sem validade jurídica",
        })
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps({"documents": documents}), "utf-8")
    scope = {"version": "fixture-v1", "max_characters": 90, "overlap_characters": 10,
             "sources": {name: {"mode": "full_text"} for name in ["alpha", "beta"]}}
    index_dir = tmp_path / "index"
    build_index(corpus_path, index_dir, FixtureEncoder(), scope)
    return corpus_path, index_dir, scope


def retriever_from(bundle):
    corpus_path, index_dir, scope = bundle
    return Retriever(corpus_path, index_dir, FixtureEncoder(), scope)


def test_article_boundaries_and_annex_exclusion():
    text = "Cabeçalho\nArt.\n1º Fixture alpha.\nArt. 2º Fixture beta.\nANEXO I\nFixture anexo."
    chosen = sections(text, {"mode": "selected_articles", "articles": ["2"]})
    assert len(chosen) == 1
    assert chosen[0]["section"] == "Art. 2"
    assert text[chosen[0]["start"]:chosen[0]["end"]] == "Art. 2º Fixture beta.\n"


def test_article_suffix_and_missing_article():
    text = "Art. 7º Fixture A\nArt. 7-A. Fixture B\nArt. 8º Fixture C"
    chosen = sections(text, {"mode": "selected_articles", "articles": ["7-A"]})
    assert len(chosen) == 1 and chosen[0]["section"] == "Art. 7-A"
    with pytest.raises(ValueError, match="não encontrados"):
        sections(text, {"mode": "selected_articles", "articles": ["99"]})


def test_chunks_preserve_article_context_and_offsets():
    text = "Art. 1º Fixture alpha " + "trecho técnico " * 50 + "\nArt. 2º Fixture beta."
    corpus = {"documents": [{"id": "fixture", "document_id": "fixture:1", "text": text}]}
    scope = {"version": "fixture", "max_characters": 120, "overlap_characters": 20,
             "sources": {"fixture": {"mode": "selected_articles", "articles": ["1", "2"]}}}
    chunks = prepare_chunks(corpus, scope)
    for chunk in chunks:
        assert chunk["text"] == text[chunk["start_char"]:chunk["end_char"]]
        assert not ("Art. 1" in chunk["text"] and "Art. 2" in chunk["text"])
    assert chunks[-1]["section"] == "Art. 2"


def test_mean_pool_ignores_padding_and_normalizes():
    hidden = np.array([[[3, 4], [900, 900]]], dtype=np.float32)
    result = mean_pool(hidden, np.array([[1, 0]]))
    np.testing.assert_allclose(result, [[0.6, 0.8]], atol=1e-6)


@pytest.mark.parametrize("value", [0, np.nan, np.inf])
def test_invalid_embeddings_rejected(value):
    with pytest.raises(ValueError):
        mean_pool(np.full((1, 2, 3), value, dtype=np.float32), np.ones((1, 2)))


def test_ranked_search_has_provenance(bundle):
    result = retriever_from(bundle).search("buscar beta", 2)
    assert result.results[0].source_id == "beta"
    assert result.results[0].score == pytest.approx(1)
    assert result.results[1].source_id == "alpha"
    assert result.results[0].url == "https://www.gov.br/fixture-beta"
    assert "não é" in result.notice
    assert result.model_revision == model_spec()["revision"]


@pytest.mark.parametrize("file", ["snapshot.json", "vectors.npy"])
def test_corrupted_artifacts_rejected(bundle, file):
    corpus_path, index_dir, scope = bundle
    manifest = json.loads((index_dir / "current.json").read_text("utf-8"))
    path = index_dir / manifest["generation"] / file
    path.write_bytes(path.read_bytes() + b"corrupted")
    with pytest.raises(IndexUnavailable, match="Integridade"):
        load_bundle(corpus_path, index_dir, scope)


def test_changed_corpus_or_scope_rejected(bundle):
    corpus_path, index_dir, scope = bundle
    retriever = retriever_from(bundle)
    with pytest.raises(IndexUnavailable, match="desatualizado"):
        load_bundle(corpus_path, index_dir, {**scope, "version": "changed"})
    corpus_path.write_bytes(corpus_path.read_bytes() + b" ")
    with pytest.raises(IndexUnavailable):
        load_bundle(corpus_path, index_dir, scope)
    with pytest.raises(IndexUnavailable):
        retriever.search("buscar alpha")


def test_missing_index_and_path_traversal_rejected(bundle, tmp_path):
    corpus_path, index_dir, scope = bundle
    with pytest.raises(IndexUnavailable):
        load_bundle(corpus_path, tmp_path / "missing", scope)
    pointer = index_dir / "current.json"
    manifest = json.loads(pointer.read_text("utf-8"))
    manifest["generation"] = "../../other"
    pointer.write_text(json.dumps(manifest), "utf-8")
    with pytest.raises(IndexUnavailable, match="Identificador"):
        load_bundle(corpus_path, index_dir, scope)


def test_failed_rebuild_preserves_active_index(bundle):
    corpus_path, index_dir, scope = bundle
    previous = (index_dir / "current.json").read_bytes()

    class BrokenEncoder:
        def encode(self, texts, kind):
            raise RuntimeError("Falha técnica de teste")

    with pytest.raises(RuntimeError):
        build_index(corpus_path, index_dir, BrokenEncoder(), scope)
    assert (index_dir / "current.json").read_bytes() == previous


def test_cached_search_rejects_broken_pointer(bundle):
    retriever = retriever_from(bundle)
    (bundle[1] / "current.json").write_text("{invalid", "utf-8")
    with pytest.raises(IndexUnavailable):
        retriever.search("buscar alpha")


def test_sources_without_model_or_corpus(monkeypatch, tmp_path):
    import app.retrieval as retrieval

    monkeypatch.setattr(retrieval, "CORPUS_PATH", tmp_path / "missing-corpus.json")
    monkeypatch.setattr(retrieval, "INDEX_DIR", tmp_path / "missing-index")
    inventory = retrieval.source_inventory()
    assert inventory["index_status"] == "not_built"
    assert len(inventory["sources"]) == 3
    assert all(not source["collected"] and source["indexed_chunks"] == 0 for source in inventory["sources"])


def test_api_search_contract_and_validation(bundle):
    app.dependency_overrides[get_retriever] = lambda: retriever_from(bundle)
    try:
        client = TestClient(app)
        response = client.post("/search", json={"question": "buscar beta", "top_k": 2})
        assert response.status_code == 200
        assert response.json()["results"][0]["source_id"] == "beta"
        for payload in [
            {"question": "   "}, {"question": "aa"}, {"question": "a" * 501},
            {"question": "buscar beta", "top_k": 0},
            {"question": "buscar beta", "top_k": 11},
            {"question": "buscar beta", "top_k": True},
            {"question": "buscar beta", "extra": "fixture"},
        ]:
            assert client.post("/search", json=payload).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_api_returns_503_for_unavailable_search(monkeypatch):
    import app.main as main

    def unavailable():
        raise IndexUnavailable("Fixture de índice ausente")

    main.get_retriever.cache_clear()
    monkeypatch.setattr(main, "Retriever", unavailable)
    try:
        response = TestClient(app).post("/search", json={"question": "buscar algo"})
        assert response.status_code == 503
    finally:
        main.get_retriever.cache_clear()
