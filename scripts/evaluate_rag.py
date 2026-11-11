"""Avalia o RAG real; erros operacionais não contam como abstenções corretas."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from app.embeddings import sha256_file
from app.ingestion import ROOT
from app.llm import GroqLLM, LLMError, read_settings
from app.rag import AnswerService, AskInput, PROMPT_SHA256, PROMPT_VERSION
from app.retrieval import IndexUnavailable, Retriever
from scripts.evaluate_retrieval import matches


def evaluate_case(service, case):
    expected = "answered" if case["evidence"] else "abstained"
    result = service.ask(AskInput(question=case["question"]))
    citations = [citation.model_dump() for citation in result.citations]
    # Confere rótulos de recuperação, não equivalência semântica da resposta.
    anchored = all(any(matches({**citation, "text": citation["quote"]}, alternative)
                       for citation in citations for alternative in item["alternatives"])
                   for item in case["evidence"]) if case["evidence"] else None
    cited = {identifier for claim in result.claims for identifier in claim.citation_ids}
    available = {citation.id for citation in result.citations}
    return {
        "id": case["id"], "split": case["split"], "category": case["category"],
        "expected_status": expected, "observed_status": result.status,
        "decision_matches_reference": result.status == expected,
        "reference_anchors_in_quotes": anchored,
        "claims_with_citations": sum(bool(claim.citation_ids) for claim in result.claims),
        "citation_links_valid": cited <= available,
        "output": result.model_dump(), "human_support_review": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", dest="case_ids", help="ID do caso; pode ser repetido.")
    parser.add_argument("--delay", type=float, default=65, help="Intervalo entre perguntas, em segundos.")
    args = parser.parse_args()
    if args.delay < 0:
        parser.error("--delay deve ser não negativo")
    dataset_path = ROOT / "evaluation/questions.json"
    dataset = json.loads(dataset_path.read_text("utf-8"))
    known = {case["id"] for case in dataset["cases"]}
    if args.case_ids and set(args.case_ids) - known:
        parser.error("ID de avaliação desconhecido")
    cases = [case for case in dataset["cases"] if not args.case_ids or case["id"] in args.case_ids]
    destination = ROOT / "reports/rag-evaluation.json"
    if destination.exists():
        parser.error("O relatório já existe. Preserve ou renomeie reports/rag-evaluation.json antes de outra execução.")
    try:
        settings = read_settings()
        retriever = Retriever()
    except (LLMError, IndexUnavailable, ValueError, ImportError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    service = AnswerService(retriever, GroqLLM(settings))
    report = {
        "started_at": datetime.now(timezone.utc).isoformat(), "run_status": "running",
        "backend": "real_external_service", "provider": settings.provider, "model": settings.model,
        "dataset_version": dataset["version"], "dataset_sha256": sha256_file(dataset_path),
        "selected_cases": [case["id"] for case in cases],
        "prompt_version": PROMPT_VERSION, "prompt_sha256": PROMPT_SHA256,
        "corpus_sha256": retriever.manifest["corpus_sha256"],
        "index_generation": retriever.manifest["generation"], "cases": [],
        "limitations": [
            "Conjunto pequeno, reutilizado da avaliação de recuperação; sem representatividade estatística.",
            "Correspondência de âncoras é uma verificação parcial, não uma avaliação semântica independente.",
            "Geração e revisão usam o mesmo modelo em chamadas separadas e podem compartilhar erros.",
            "Cobertura de citações e correspondência literal não garantem correção jurídica.",
            "Revisão humana de suporte e atualidade permanece pendente em cada caso.",
        ],
    }
    destination.parent.mkdir(exist_ok=True)

    def save():
        rows = report["cases"]
        completed = [row for row in rows if "output" in row]
        report["summary"] = {
            "attempted": len(rows), "completed": len(completed),
            "operational_errors": len(rows) - len(completed),
            "decision_matches": sum(row["decision_matches_reference"] for row in completed),
            "answered": sum(row["observed_status"] == "answered" for row in completed),
            "abstained": sum(row["observed_status"] == "abstained" for row in completed),
            "reference_anchors_matched": sum(row["reference_anchors_in_quotes"] is True for row in completed),
        }
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
        temporary.replace(destination)

    try:
        for index, case in enumerate(cases):
            if index:
                time.sleep(args.delay)
            try:
                row = evaluate_case(service, case)
            except (LLMError, IndexUnavailable) as exc:
                row = {"id": case["id"], "operational_error": str(exc),
                       "http_status": getattr(exc, "status_code", 503)}
                report["cases"].append(row)
                report["run_status"] = "stopped_on_error"
                save()
                print(f"Interrompida: {case['id']}. {exc}", flush=True)
                return 1
            report["cases"].append(row)
            save()
            print(f"{case['id']}: {row['observed_status']}", flush=True)
    except KeyboardInterrupt:
        report["run_status"] = "interrupted"
        save()
        return 1
    report["run_status"] = "completed"
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
