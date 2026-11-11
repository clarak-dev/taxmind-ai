from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException

from app.retrieval import IndexUnavailable, Retriever, SearchInput, SearchOutput, source_inventory

from app.simulator import SimulationInput, SimulationOutput, simulate

app = FastAPI(
    title="TaxMind AI",
    version="0.2.0",
    description=(
        "Simulação hipotética e recuperação semântica de documentos oficiais. "
        "A busca retorna trechos candidatos; geração por LLM ainda não implementada."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version, "rag_status": "not_implemented"}


@app.post("/simulate", response_model=SimulationOutput)
def simulate_endpoint(request: SimulationInput) -> SimulationOutput:
    return simulate(request)


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    try:
        return Retriever()
    except (IndexUnavailable, ValueError, ImportError) as exc:
        raise HTTPException(status_code=503, detail="Busca indisponível. Prepare o modelo e construa um índice válido.") from exc


@app.post("/search", response_model=SearchOutput)
def search_endpoint(request: SearchInput, retriever: Retriever = Depends(get_retriever)) -> SearchOutput:
    try:
        return retriever.search(request.question, request.top_k)
    except IndexUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/sources")
def sources_endpoint() -> dict:
    try:
        return source_inventory()
    except (ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail="Catálogo ou corpus documental inválido.") from exc
