"""Índice vetorial exato, versionado pelo corpus, recorte e modelo."""

import argparse
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from app.chunking import prepare_chunks
from app.embeddings import E5Embedder, model_fingerprint, model_spec, sha256_file
from app.ingestion import ROOT, read_sources

CORPUS_PATH = ROOT / "data/processed/corpus.json"
INDEX_DIR = ROOT / "data/index"
SCOPE_PATH = ROOT / "config/retrieval_scope.json"


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class IndexUnavailable(ValueError):
    pass


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=10, strict=True)


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    section: str
    score: float
    text: str
    title: str
    url: str
    accessed_at: str
    temporal_scope: str
    legal_validity: str
    start_char: int
    end_char: int


class SearchOutput(BaseModel):
    question: str
    results: list[SearchHit]
    model_id: str
    model_revision: str
    index_generation: str
    latency_ms: float
    notice: str = (
        "Trechos candidatos por similaridade, sem resposta gerada. O score não é "
        "probabilidade de acerto nem comprovação de suporte. Vigência, exceções e "
        "remissões precisam ser verificadas; a LC 214 está indexada parcialmente."
    )


def read_corpus(path: Path) -> dict:
    corpus = json.loads(path.read_text("utf-8"))
    if not corpus.get("documents"):
        raise ValueError("Corpus sem documentos.")
    identifiers = [document["id"] for document in corpus["documents"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Corpus com fontes duplicadas.")
    for document in corpus["documents"]:
        digest = hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
        if digest != document["text_sha256"]:
            raise ValueError("O texto do corpus não corresponde ao hash coletado.")
    return corpus


def build_index(corpus_path=CORPUS_PATH, index_dir=INDEX_DIR, embedder=None, scope=None) -> dict:
    started = time.perf_counter()
    corpus_sha = sha256_file(corpus_path)
    corpus = read_corpus(corpus_path)
    scope = scope if scope is not None else json.loads(SCOPE_PATH.read_text("utf-8"))
    chunks = prepare_chunks(corpus, scope)
    encoder = embedder if embedder is not None else E5Embedder()
    spec = model_spec()
    vectors = encoder.encode([chunk["text"] for chunk in chunks], "passage")
    if (
        vectors.shape != (len(chunks), spec["dimensions"])
        or not np.isfinite(vectors).all()
        or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
    ):
        raise ValueError("Embeddings incompatíveis, não finitos ou sem normalização L2.")
    if sha256_file(corpus_path) != corpus_sha:
        raise ValueError("O corpus foi alterado durante a indexação. Índice anterior preservado.")
    generation = "build-" + uuid.uuid4().hex
    folder = index_dir / generation
    folder.mkdir(parents=True)
    np.save(folder / "vectors.npy", vectors.astype(np.float32), allow_pickle=False)
    documents = [
        {key: value for key, value in doc.items() if key != "text"}
        for doc in corpus["documents"] if doc["id"] in scope["sources"]
    ]
    snapshot = {"documents": documents, "chunks": chunks, "scope": scope}
    (folder / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), "utf-8")
    manifest = {
        "schema_version": 1, "generation": generation,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": corpus_sha, "scope_sha256": fingerprint(scope),
        "model_fingerprint": model_fingerprint(spec), "model": spec,
        "vectors_sha256": sha256_file(folder / "vectors.npy"),
        "snapshot_sha256": sha256_file(folder / "snapshot.json"),
        "chunk_count": len(chunks), "document_count": len(documents),
        "dimensions": vectors.shape[1], "search": "exact-normalized-dot-product",
        "build_seconds": round(time.perf_counter() - started, 3),
    }
    temporary = index_dir / "current.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    temporary.replace(index_dir / "current.json")
    return manifest


def load_bundle(corpus_path=CORPUS_PATH, index_dir=INDEX_DIR, scope=None):
    try:
        manifest = json.loads((index_dir / "current.json").read_text("utf-8"))
        generation = manifest["generation"]
        if not (generation.startswith("build-") and len(generation) == 38 and all(c in "0123456789abcdef" for c in generation[6:])):
            raise IndexUnavailable("Identificador de índice inválido.")
        scope = scope if scope is not None else json.loads(SCOPE_PATH.read_text("utf-8"))
        if (
            manifest["corpus_sha256"] != sha256_file(corpus_path)
            or manifest["model_fingerprint"] != model_fingerprint(model_spec())
            or manifest["scope_sha256"] != fingerprint(scope)
        ):
            raise IndexUnavailable("Índice desatualizado; execute python -m app.retrieval build.")
        folder = index_dir / generation
        for filename, key in [("snapshot.json", "snapshot_sha256"), ("vectors.npy", "vectors_sha256")]:
            if sha256_file(folder / filename) != manifest[key]:
                raise IndexUnavailable("Integridade do índice inválida; reconstrua o índice.")
        snapshot = json.loads((folder / "snapshot.json").read_text("utf-8"))
        vectors = np.load(folder / "vectors.npy", allow_pickle=False)
        if (
            vectors.shape != (len(snapshot["chunks"]), manifest["dimensions"])
            or len(snapshot["chunks"]) != manifest["chunk_count"]
            or not np.isfinite(vectors).all()
            or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4)
        ):
            raise IndexUnavailable("Matriz do índice inválida.")
        return manifest, snapshot, vectors
    except IndexUnavailable:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise IndexUnavailable("Índice ausente ou inválido; execute python -m app.retrieval build.") from exc


class Retriever:
    def __init__(self, corpus_path=CORPUS_PATH, index_dir=INDEX_DIR, embedder=None, scope=None):
        self.corpus_path, self.index_dir = corpus_path, index_dir
        self.scope = scope
        self.manifest, self.snapshot, self.vectors = load_bundle(corpus_path, index_dir, scope)
        self.embedder = embedder if embedder is not None else E5Embedder()
        self.documents = {doc["document_id"]: doc for doc in self.snapshot["documents"]}

    def search(self, question: str, top_k=5) -> SearchOutput:
        request = SearchInput(question=question, top_k=top_k)
        started = time.perf_counter()
        try:
            current = json.loads((self.index_dir / "current.json").read_text("utf-8"))
            active_scope = self.scope if self.scope is not None else json.loads(SCOPE_PATH.read_text("utf-8"))
            current_generation = current["generation"]
            corpus_sha = sha256_file(self.corpus_path)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise IndexUnavailable("Índice ou corpus indisponível; reconstrua o índice e reinicie a API.") from exc
        if (
            current_generation != self.manifest["generation"]
            or corpus_sha != self.manifest["corpus_sha256"]
            or fingerprint(active_scope) != self.manifest["scope_sha256"]
            or model_fingerprint(model_spec()) != self.manifest["model_fingerprint"]
        ):
            raise IndexUnavailable("Índice alterado ou corpus desatualizado; reconstrua o índice e reinicie a API.")
        query = self.embedder.encode([request.question], "query")[0]
        if query.shape != (self.manifest["dimensions"],) or not np.isfinite(query).all() or not np.isclose(np.linalg.norm(query), 1, atol=1e-4):
            raise ValueError("Embedding de pergunta inválido.")
        scores = self.vectors @ query
        ranking = np.argsort(-scores, kind="stable")[:request.top_k]
        hits = []
        for row in ranking:
            chunk = self.snapshot["chunks"][int(row)]
            document = self.documents[chunk["document_id"]]
            hits.append(SearchHit(
                chunk_id=chunk["id"], document_id=chunk["document_id"], source_id=chunk["source_id"],
                section=chunk["section"], score=float(np.clip(scores[row], -1, 1)), text=chunk["text"],
                title=document["title"], url=document["url"], accessed_at=document["accessed_at"],
                temporal_scope=document["temporal_scope"], legal_validity=document["legal_validity"],
                start_char=chunk["start_char"], end_char=chunk["end_char"],
            ))
        return SearchOutput(
            question=request.question, results=hits,
            model_id=self.manifest["model"]["model_id"], model_revision=self.manifest["model"]["revision"],
            index_generation=self.manifest["generation"], latency_ms=round((time.perf_counter() - started) * 1000, 3),
        )


def source_inventory() -> dict:
    sources = read_sources(ROOT / "data/sources.json")
    corpus = read_corpus(CORPUS_PATH) if CORPUS_PATH.exists() else {"documents": []}
    collected = {doc["id"]: doc for doc in corpus["documents"]}
    snapshot = {"chunks": []}
    state = "not_built"
    if (INDEX_DIR / "current.json").exists():
        try:
            _, snapshot, _ = load_bundle()
            state = "validated"
        except IndexUnavailable:
            state = "stale_or_invalid"
    scope = json.loads(SCOPE_PATH.read_text("utf-8"))
    return {"index_status": state, "scope": scope, "sources": [
        {"id": source.id, "title": source.title, "url": source.url,
         "collected": source.id in collected,
         "accessed_at": collected.get(source.id, {}).get("accessed_at"),
         "indexed_chunks": sum(chunk["source_id"] == source.id for chunk in snapshot["chunks"]),
         "legal_validity": source.legal_validity}
        for source in sources
    ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "search"])
    parser.add_argument("--question")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.action == "build":
        result = build_index()
        (ROOT / "reports/index.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
        print(json.dumps({k: result[k] for k in ["chunk_count", "document_count", "dimensions", "build_seconds"]}))
    else:
        if not args.question:
            parser.error("search exige --question")
        result = Retriever().search(args.question, args.top_k)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
