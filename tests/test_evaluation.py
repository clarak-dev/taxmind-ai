import pytest

from scripts.evaluate_retrieval import LexicalBaseline, measure


def test_metrics_require_correct_source_section_and_anchor():
    evidence = [{"alternatives": [{"source_id": "fixture", "section": "Art. 1", "anchor": "Fixture técnica"}]}]
    wrong = {"source_id": "other", "section": "Art. 1", "text": "Fixture técnica"}
    right = {"source_id": "fixture", "section": "Art. 1", "text": "FIXTURE\ntécnica"}
    assert measure([wrong, right], evidence, 1) == {"hit": 0, "evidence_recall": 0, "reciprocal_rank": 0}
    assert measure([wrong, right], evidence, 2) == {"hit": 1, "evidence_recall": 1, "reciprocal_rank": 0.5}
    assert measure([right], [], 5) is None


def test_partial_evidence_is_not_full_recall():
    evidence = [{"alternatives": [{"source_id": "fixture", "anchor": anchor}]} for anchor in ["alpha", "beta"]]
    hit = {"source_id": "fixture", "text": "alpha", "section": "Fixture"}
    assert measure([hit], evidence, 5)["evidence_recall"] == pytest.approx(0.5)


def test_lexical_baseline_uses_document_vocabulary_and_stable_ties():
    chunks = [{"id": "a", "text": "alpha"}, {"id": "b", "text": "beta"}]
    baseline = LexicalBaseline(chunks)
    assert baseline.search("beta", 1)[0]["chunk_id"] == "b"
    unknown = baseline.search("unknown", 2)
    assert [hit["chunk_id"] for hit in unknown] == ["a", "b"]
    assert all(hit["score"] == 0 for hit in unknown)
