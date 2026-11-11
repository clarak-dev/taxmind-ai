"""Avaliação por âncoras de evidência; não mede geração nem aconselhamento jurídico."""

import hashlib
import json
import math
import re
import statistics
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone

from app.embeddings import sha256_file
from app.ingestion import ROOT
from app.retrieval import Retriever, read_corpus


def normalize(text):
    return " ".join(text.casefold().split())


def matches(hit, alternative):
    return (
        hit["source_id"] == alternative["source_id"]
        and (not alternative.get("section") or hit["section"] == alternative["section"])
        and normalize(alternative["anchor"]) in normalize(hit["text"])
    )


def measure(hits, evidence, k):
    if not evidence:
        return None
    matched = [any(matches(hit, alt) for hit in hits[:k] for alt in item["alternatives"]) for item in evidence]
    first = next((rank for rank, hit in enumerate(hits[:k], 1) if any(
        matches(hit, alt) for item in evidence for alt in item["alternatives"]
    )), None)
    return {"hit": int(any(matched)), "evidence_recall": sum(matched) / len(matched),
            "reciprocal_rank": 1 / first if first else 0}


def terms(text):
    text = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    return Counter(re.findall(r"\b\w{2,}\b", text))


class LexicalBaseline:
    """TF-IDF com log-TF e cosseno; vocabulário ajustado somente nos documentos."""

    def __init__(self, chunks):
        self.chunks = chunks
        counts = [terms(chunk["text"]) for chunk in chunks]
        frequency = Counter(word for count in counts for word in count)
        self.idf = {word: math.log((1 + len(chunks)) / (1 + count)) + 1 for word, count in frequency.items()}
        self.vectors = [self.vector(count) for count in counts]

    def vector(self, counts):
        weights = {word: (1 + math.log(count)) * self.idf[word] for word, count in counts.items() if word in self.idf}
        norm = math.sqrt(sum(value * value for value in weights.values())) or 1
        return {word: value / norm for word, value in weights.items()}

    def search(self, question, k):
        query = self.vector(terms(question))
        scores = [sum(query.get(word, 0) * weight for word, weight in document.items()) for document in self.vectors]
        ranking = sorted(range(len(scores)), key=lambda index: (-scores[index], index))[:k]
        return [{**self.chunks[index], "chunk_id": self.chunks[index]["id"], "score": scores[index]} for index in ranking]


def summarize(rows, method, split):
    chosen = [row for row in rows if row["split"] == split and row["metrics"][method] is not None]
    return {"questions": len(chosen), **{
        f"{metric}@{k}": statistics.mean(row["metrics"][method][str(k)][metric] for row in chosen)
        for k in [1, 3, 5] for metric in ["hit", "evidence_recall", "reciprocal_rank"]
    }}


def compact_hit(hit):
    keys = ["chunk_id", "document_id", "source_id", "section", "score", "start_char", "end_char", "title", "url"]
    return {**{key: hit[key] for key in keys if key in hit},
            "text_sha256": hashlib.sha256(hit["text"].encode("utf-8")).hexdigest()}


def main():
    questions_path = ROOT / "evaluation/questions.json"
    dataset = json.loads(questions_path.read_text("utf-8"))
    cold_start = time.perf_counter()
    retriever = Retriever()
    load_seconds = time.perf_counter() - cold_start
    baseline = LexicalBaseline(retriever.snapshot["chunks"])
    corpus = read_corpus(retriever.corpus_path)
    documents = {doc["document_id"]: doc for doc in corpus["documents"]}
    # Falha antes de pontuar se uma âncora rotulada não existir no recorte indexado.
    for case in dataset["cases"]:
        for evidence in case["evidence"]:
            if not any(matches(chunk, alt) for chunk in retriever.snapshot["chunks"] for alt in evidence["alternatives"]):
                raise ValueError(f"Âncora não localizada no recorte: {case['id']}")
    rows = []
    for case in dataset["cases"]:
        result = retriever.search(case["question"], 5)
        semantic = [hit.model_dump() for hit in result.results]
        lexical_start = time.perf_counter()
        lexical = baseline.search(case["question"], 5)
        lexical_ms = (time.perf_counter() - lexical_start) * 1000
        for hit in semantic:
            doc = documents[hit["document_id"]]
            assert hit["text"] == doc["text"][hit["start_char"]:hit["end_char"]]
            assert hit["url"] == doc["url"] and hit["title"] == doc["title"]
        rows.append({
            **case, "semantic_latency_ms": result.latency_ms, "lexical_latency_ms": round(lexical_ms, 3),
            "metrics": {name: {str(k): measure(hits, case["evidence"], k) for k in [1, 3, 5]} if case["evidence"] else None
                        for name, hits in [("semantic", semantic), ("lexical_tfidf", lexical)]},
            "semantic": semantic, "lexical_tfidf": lexical,
        })
        print(f"Avaliada: {case['id']}", flush=True)
    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_sha256": sha256_file(questions_path), "dataset_version": dataset["version"],
        "model": retriever.manifest["model"], "corpus_sha256": retriever.manifest["corpus_sha256"],
        "scope_sha256": retriever.manifest["scope_sha256"],
        "index_generation": retriever.manifest["generation"], "chunk_count": len(retriever.snapshot["chunks"]),
        "question_count": len(rows), "model_load_seconds": round(load_seconds, 3),
        "provenance_checks": {"checked_hits": sum(len(row["semantic"]) for row in rows), "all_passed": True},
        "summary": {method: {split: summarize(rows, method, split) for split in ["development", "test"]}
                    for method in ["semantic", "lexical_tfidf"]},
        "semantic_latency_ms": {"median": statistics.median(row["semantic_latency_ms"] for row in rows),
                                "maximum": max(row["semantic_latency_ms"] for row in rows)},
        "scope": retriever.snapshot["scope"], "cases": [
            {**row, "semantic": [compact_hit(hit) for hit in row["semantic"]],
             "lexical_tfidf": [compact_hit(hit) for hit in row["lexical_tfidf"]]}
            for row in rows
        ],
        "limitations": [
            "Rótulos parciais por âncoras: trechos relevantes não rotulados podem ser contados como falha.",
            "Amostra pequena; há perguntas que mencionam números de artigos e favorecem correspondência lexical.",
            "Desenvolvimento e teste registrados separadamente; nenhum limiar de score foi calibrado.",
            "Diagnósticos fora do escopo recebem vizinhos; não há classificador de escopo ou abstenção automática.",
            "Não mede respostas geradas, suporte de afirmações, causalidade ou correção tributária.",
            "Latência após carregar o modelo; resultados dependem da máquina e do estado do cache.",
        ],
    }
    destination = ROOT / "reports/retrieval-evaluation.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(report["summary"], ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
