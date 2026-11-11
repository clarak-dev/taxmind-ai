from fastapi import FastAPI

from app.simulator import SimulationInput, SimulationOutput, simulate

app = FastAPI(
    title="TaxMind AI",
    version="0.1.0",
    description=(
        "Simulação hipotética e preparação de documentos públicos para RAG. "
        "Recuperação semântica e geração por LLM ainda não implementadas."
    ),
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version, "rag_status": "not_implemented"}


@app.post("/simulate", response_model=SimulationOutput)
def simulate_endpoint(request: SimulationInput) -> SimulationOutput:
    return simulate(request)
