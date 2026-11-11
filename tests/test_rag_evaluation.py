from scripts.evaluate_rag import evaluate_case
from tests.test_rag import FixtureLLM, FixtureRetriever
from app.rag import AnswerService


def test_evaluation_separates_decision_from_reference_evidence():
    service = AnswerService(FixtureRetriever(), FixtureLLM())
    case = {
        "id": "fixture", "split": "development", "category": "numeric", "question": "Qual é a taxa da fixture?",
        "evidence": [{"alternatives": [{"source_id": "fixture", "section": "Fixture", "anchor": "0,1%"}]}],
    }
    row = evaluate_case(service, case)
    assert row["decision_matches_reference"] is True
    assert row["reference_anchors_in_quotes"] is True
    assert row["human_support_review"] == "pending"
    case["evidence"][0]["alternatives"][0]["anchor"] = "999%"
    row = evaluate_case(service, case)
    assert row["decision_matches_reference"] is True
    assert row["reference_anchors_in_quotes"] is False


def test_unsupported_answer_does_not_count_as_correct_diagnostic():
    case = {"id": "ood", "split": "diagnostic", "category": "out_of_scope",
            "question": "Pergunta fora do escopo", "evidence": []}
    row = evaluate_case(AnswerService(FixtureRetriever(), FixtureLLM()), case)
    assert row["expected_status"] == "abstained"
    assert row["decision_matches_reference"] is False
    assert row["reference_anchors_in_quotes"] is None
