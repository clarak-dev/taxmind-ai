from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException

from app.llm import GroqLLM, LLMError, read_settings
from app.rag import AnswerService, AskInput, AskOutput
from app.retrieval import IndexUnavailable, Retriever, SearchInput, SearchOutput, source_inventory

from app.simulator import SimulationInput, SimulationOutput, simulate

app = FastAPI(
    title="TaxMind AI",
    version="0.3.0",
    description=(
        "Simulação hipotética e recuperação semântica de documentos oficiais. "
        "Respostas com LLM, citações verificáveis e revisão de suporte."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        read_settings()
        rag_status = "configured"
    except LLMError:
        rag_status = "not_configured"
    return {"status": "ok", "version": app.version, "rag_status": rag_status}


@app.post("/simulate", response_model=SimulationOutput)
def simulate_endpoint(request: SimulationInput) -> SimulationOutput:
    return simulate(request)


@lru_cache(maxsize=1)
def get_retriever() -> Retriever:
    try:
        return Retriever()
    except (IndexUnavailable, ValueError, ImportError) as exc:
        raise HTTPException(status_code=503, detail="Busca indisponível. Prepare o modelo e construa um índice válido.") from exc


def get_llm() -> GroqLLM:
    try:
        return GroqLLM(read_settings())
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def get_answer_service(llm=Depends(get_llm), retriever=Depends(get_retriever)) -> AnswerService:
    return AnswerService(retriever, llm)


@app.post("/ask", response_model=AskOutput)
def ask_endpoint(request: AskInput, service=Depends(get_answer_service)) -> AskOutput:
    try:
        return service.ask(request)
    except LLMError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except IndexUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Pergunta incompatível com a busca disponível.") from exc


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
