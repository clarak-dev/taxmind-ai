import hashlib
import json

import httpx
import pytest

from app.ingestion import ROOT, Source, chunk_text, extract_text, ingest, read_sources, validate_url


@pytest.fixture
def source():
    return Source(
        id="technical-fixture", title="Fixture técnica sintética, sem conteúdo jurídico",
        publisher="Fixture", url="https://www.gov.br/fixture",
        selector="#content-core", expected_text="Fixture técnica",
        temporal_scope="Apenas teste", legal_validity="Não é documento legal",
    )


@pytest.fixture
def html():
    return (
        '<html><meta charset="utf-8"><title>Fixture técnica</title>'
        '<nav>NAVEGACAO_FORA</nav><div id="content-core">'
        '<script>SCRIPT_FORA</script><s>REVOGADO_FORA</s><del>REMOVIDO_FORA</del>'
        + "<p>Fixture técnica para testar extração, sem afirmações jurídicas.</p>" * 35
        + "</div><footer>RODAPE_FORA</footer></html>"
    )


def test_catalog_has_three_distinct_official_sources():
    sources = read_sources(ROOT / "data/sources.json")
    assert len(sources) == 3
    assert len({source.id for source in sources}) == 3
    assert any("camara" in source.url for source in sources)


def test_extracts_content_without_navigation_scripts_or_deleted_text(source, html):
    text = extract_text(html, source)
    assert "extração" in text
    assert "_FORA" not in text


@pytest.mark.parametrize("html", [
    "<html><title>Acesso Negado!</title></html>",
    '<div id="content-core">Fixture técnica</div>',
    '<div id="other">' + "Fixture técnica " * 40 + "</div>",
    '<div id="content-core">' + "conteúdo inesperado " * 40 + "</div>",
    '<div id="content-core">' + "Fixture técnica \ufffd " * 40 + "</div>",
])
def test_rejects_block_missing_content_and_bad_encoding(source, html):
    with pytest.raises(ValueError):
        extract_text(html, source)


@pytest.mark.parametrize("url", [
    "http://www.gov.br/fixture", "https://example.com/fixture",
    "https://www.gov.br.evil.example/fixture", "https://www.gov.br:8443/fixture",
    "https://user:pass@www.gov.br/fixture", "file:///etc/passwd",
])
def test_rejects_urls_outside_official_catalog(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_chunks_preserve_text_offsets_and_full_coverage():
    text = "Documento técnico sintético com acentuação e conteúdo de teste. " * 50
    chunks = chunk_text(text, size=200, overlap=35)
    assert chunks[0]["start_char"] == 0
    assert chunks[-1]["end_char"] == len(text)
    for chunk in chunks:
        assert chunk["text"] == text[chunk["start_char"]:chunk["end_char"]]
        assert 0 < len(chunk["text"]) <= 200
    for left, right in zip(chunks, chunks[1:]):
        assert left["start_char"] < right["start_char"] <= left["end_char"]


@pytest.mark.parametrize("size,overlap", [(0, 0), (10, 10), (10, -1)])
def test_invalid_chunk_configuration(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("fixture", size, overlap)


def test_ingestion_provenance_and_stable_ids(tmp_path, source, html):
    transport = httpx.MockTransport(lambda request: httpx.Response(
        200, text=html, headers={"content-type": "text/html; charset=utf-8"},
    ))
    with httpx.Client(transport=transport) as client:
        first = ingest([source], tmp_path, client)
        second = ingest([source], tmp_path, client)
    assert [c["id"] for c in first["chunks"]] == [c["id"] for c in second["chunks"]]
    doc = first["documents"][0]
    assert doc["raw_sha256"] == hashlib.sha256(html.encode()).hexdigest()
    assert (tmp_path / doc["raw_path"]).read_bytes() == html.encode()
    assert doc["accessed_at"].endswith("+00:00")
    assert json.loads((tmp_path / "processed/corpus.json").read_text("utf-8"))["chunks"]


def test_failure_preserves_previous_corpus(tmp_path, source, html):
    output = tmp_path / "processed/corpus.json"
    output.parent.mkdir()
    output.write_text('{"previous": true}', "utf-8")
    second = source.model_copy(update={"id": "second", "url": "https://www.gov.br/second"})
    transport = httpx.MockTransport(lambda request: httpx.Response(
        500 if request.url.path == "/second" else 200,
        text=html, headers={"content-type": "text/html; charset=utf-8"},
    ))
    with httpx.Client(transport=transport) as client, pytest.raises(httpx.HTTPStatusError):
        ingest([source, second], tmp_path, client)
    assert output.read_text("utf-8") == '{"previous": true}'


def test_external_redirect_not_requested(tmp_path, source):
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "https://example.com/blocked"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(ValueError):
        ingest([source], tmp_path, client)
    assert requests == [source.url]
    assert not (tmp_path / "processed/corpus.json").exists()


def test_non_html_response_rejected(tmp_path, source):
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(
        200, content=b"%PDF", headers={"content-type": "application/pdf"},
    ))) as client, pytest.raises(ValueError):
        ingest([source], tmp_path, client)
