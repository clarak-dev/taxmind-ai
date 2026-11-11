"""Recorte explícito do corpus sem modificar os documentos coletados."""

import re

from app.ingestion import chunk_text

ARTICLE = re.compile(r"(?m)^[ \t]*Art\.[ \t\r\n]*(\d+(?:-[A-Z])?)[º°]?(?=[\s.])")
ANNEX = re.compile(r"(?m)^[ \t]*ANEXO[ \t\r\n]+[IVXLCDM]+\b|^Brasília,")
HEADING = re.compile(
    r"(?m)^(?:\d+\. [^\n]{3,140}|20\d{2}(?: e 20\d{2}| a 20\d{2})?"
    r"|O que muda\?|Transição|Imposto Seletivo:|Tributos que [^\n]+)$"
)


def sections(text: str, selection: dict) -> list[dict]:
    if selection["mode"] == "full_text":
        headings = list(HEADING.finditer(text))
        first_label = headings[0].group().strip() if headings and headings[0].start() == 0 else "Introdução"
        boundaries = [(0, first_label)]
        boundaries.extend((m.start(), m.group().strip()) for m in headings if m.start() > 0)
    elif selection["mode"] == "selected_articles":
        markers = sorted(
            [(m.start(), m.group(1)) for m in ARTICLE.finditer(text)]
            + [(m.start(), None) for m in ANNEX.finditer(text)]
        )
        result = []
        seen = set()
        for index, (start, number) in enumerate(markers):
            if number not in selection["articles"] or number in seen:
                continue
            end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
            result.append({"start": start, "end": end, "section": f"Art. {number}"})
            seen.add(number)
        missing = set(selection["articles"]) - seen
        if missing:
            raise ValueError(f"Artigos selecionados não encontrados: {sorted(missing)}")
        return result
    else:
        raise ValueError("Modo de seleção documental desconhecido.")
    return [
        {"start": start, "end": boundaries[index + 1][0] if index + 1 < len(boundaries) else len(text), "section": label}
        for index, (start, label) in enumerate(boundaries)
    ]


def prepare_chunks(corpus: dict, scope: dict) -> list[dict]:
    documents = {document["id"]: document for document in corpus["documents"]}
    chunks = []
    for source_id, selection in scope["sources"].items():
        if source_id not in documents:
            raise ValueError(f"Fonte ainda não coletada: {source_id}")
        document = documents[source_id]
        for section in sections(document["text"], selection):
            block = document["text"][section["start"]:section["end"]]
            if not block.strip():
                continue
            for part in chunk_text(block, scope["max_characters"], scope["overlap_characters"]):
                start = section["start"] + part["start_char"]
                end = section["start"] + part["end_char"]
                chunks.append({
                    "id": f"{document['document_id']}:{scope['version']}:{start}-{end}",
                    "document_id": document["document_id"], "source_id": source_id,
                    "section": section["section"], "start_char": start, "end_char": end,
                    "text": document["text"][start:end],
                })
    if not chunks:
        raise ValueError("O recorte não produziu trechos indexáveis.")
    return chunks
