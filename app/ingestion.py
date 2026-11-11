"""Coleta controlada de HTML oficial e preparação de trechos com proveniência."""

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_HOSTS = {"www.gov.br", "www2.camara.leg.br", "www.planalto.gov.br"}


def validate_url(url: str) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or parts.hostname not in ALLOWED_HOSTS
        or parts.username
        or parts.password
        or parts.port not in (None, 443)
    ):
        raise ValueError("A coleta aceita apenas HTTPS nos portais oficiais selecionados.")
    return url


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    publisher: str
    url: str
    selector: str
    expected_text: str
    temporal_scope: str
    legal_validity: str
    _official_url = field_validator("url")(validate_url)


def read_sources(path: Path) -> list[Source]:
    sources = [Source.model_validate(item) for item in json.loads(path.read_text("utf-8"))]
    if not sources or len({source.id for source in sources}) != len(sources):
        raise ValueError("O catálogo deve ter fontes com identificadores únicos.")
    return sources


def extract_text(html: str, source: Source) -> str:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    if any(marker in title for marker in ("acesso negado", "access denied", "captcha")):
        raise ValueError("O portal retornou uma página de bloqueio.")
    container = soup.select_one(source.selector)
    if container is None:
        raise ValueError(f"Conteúdo principal ausente: {source.selector}")
    for element in container.select("script, style, nav, header, footer, s, del, strike"):
        element.decompose()
    text = "\n".join(
        line for part in container.get_text("\n").splitlines()
        if (line := re.sub(r"\s+", " ", part).strip())
    )
    if len(text) < 300 or source.expected_text.casefold() not in text.casefold():
        raise ValueError("Texto insuficiente ou marcador esperado ausente; fonte rejeitada.")
    if "\ufffd" in text:
        raise ValueError("Falha de decodificação no documento; fonte rejeitada.")
    return text


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[dict]:
    """Offsets em caracteres do texto limpo; fronteiras por palavra, com sobreposição."""
    if size < 2 or not 0 <= overlap < size:
        raise ValueError("Use size >= 2 e 0 <= overlap < size.")
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append({"start_char": start, "end_char": end, "text": text[start:end]})
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def fetch_html(client: httpx.Client, source: Source) -> httpx.Response:
    url = source.url
    for _ in range(6):
        validate_url(url)
        response = client.get(url, follow_redirects=False)
        if response.is_redirect:
            url = str(response.url.join(response.headers["location"]))
            continue
        response.raise_for_status()
        if "text/html" not in response.headers.get("content-type", "").lower():
            raise ValueError("Esta etapa aceita somente documentos HTML.")
        return response
    raise ValueError("Limite de redirecionamentos excedido.")


def ingest(sources: list[Source], data_dir: Path, client: httpx.Client) -> dict:
    documents = []
    chunks = []
    for source in sources:
        response = fetch_html(client, source)
        # A Câmara publica HTML com charset próprio; HTTPX respeita o cabeçalho.
        html = response.text
        if "charset=" not in response.headers.get("content-type", "").lower():
            detected = BeautifulSoup(response.content, "html.parser").original_encoding
            html = response.content.decode(detected or "utf-8")
        text = extract_text(html, source)
        digest = hashlib.sha256(response.content).hexdigest()
        text_digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        document_id = f"{source.id}:{text_digest[:16]}"
        source_chunks = chunk_text(text)
        for index, chunk in enumerate(source_chunks):
            chunks.append({
                **chunk, "id": f"{document_id}:{index}",
                "document_id": document_id, "source_id": source.id,
            })
        raw_path = data_dir / "raw" / source.id / f"{digest}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(response.content)
        documents.append({
            **source.model_dump(), "document_id": document_id,
            "final_url": str(response.url),
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "raw_sha256": digest, "text_sha256": text_digest,
            "last_modified": response.headers.get("last-modified"),
            "etag": response.headers.get("etag"),
            "raw_path": raw_path.relative_to(data_dir).as_posix(),
            "text": text, "chunk_count": len(source_chunks),
        })
    corpus = {"schema_version": 1, "documents": documents, "chunks": chunks}
    processed = data_dir / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    temporary = processed / "corpus.tmp"
    temporary.write_text(json.dumps(corpus, ensure_ascii=False, indent=2), "utf-8")
    temporary.replace(processed / "corpus.json")
    return corpus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=ROOT / "data/sources.json")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/ingestion.json")
    args = parser.parse_args()
    try:
        sources = read_sources(args.catalog)
        with httpx.Client(timeout=30, headers={"User-Agent": "TaxMindAI/0.1 (public-document-study)"}) as client:
            corpus = ingest(sources, args.data_dir, client)
    except (httpx.HTTPError, ValueError, OSError) as exc:
        parser.exit(1, f"Ingestão interrompida; corpus anterior preservado: {exc}\n")
    report = {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(corpus["documents"]),
        "chunk_count": len(corpus["chunks"]),
        "documents": [{k: v for k, v in doc.items() if k != "text"} for doc in corpus["documents"]],
        "limitations": [
            "Coleta não atesta vigência jurídica de cada dispositivo.",
            "Chunks por caracteres ainda precisam de segmentação por artigo/seção.",
            "Sem embeddings, recuperação semântica ou geração por LLM nesta etapa.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    print(f"Documentos: {report['document_count']}; chunks: {report['chunk_count']}")
    print(f"Relatório: {args.report}")


if __name__ == "__main__":
    main()
