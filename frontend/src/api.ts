export interface Health {
  status: string;
  version: string;
  rag_status: "configured" | "not_configured";
}

export interface Source {
  id: string;
  title: string;
  url: string;
  collected: boolean;
  accessed_at: string | null;
  indexed_chunks: number;
  legal_validity: string;
}

export interface SourceInventory {
  index_status: string;
  scope: {
    description: string;
    sources: Record<string, { mode: string; articles?: string[] }>;
  };
  sources: Source[];
}

export interface Citation {
  id: number;
  chunk_id: string;
  source_id: string;
  title: string;
  url: string;
  section: string;
  quote: string;
  accessed_at: string;
  temporal_scope: string;
  legal_validity: string;
  start_char: number;
  end_char: number;
}

export interface Answer {
  question: string;
  status: "answered" | "abstained";
  answer: string;
  claims: { text: string; citation_ids: number[] }[];
  citations: Citation[];
  reason: string;
  provider: string;
  model: string;
  prompt_version: string;
  index_generation: string;
  latency_ms: number;
  notice: string;
}

export interface SimulationInput {
  base_amount: string;
  current_rate_percent: string;
  proposed_rate_percent: string;
}

export interface Scenario {
  rate_percent: string;
  tax_amount: string;
  total_amount: string;
}

export interface Simulation {
  currency: string;
  base_amount: string;
  current: Scenario;
  proposed: Scenario;
  tax_difference: string;
  formula: string;
  rounding: string;
  disclaimer: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const base = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

async function request<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
  timeout = 15_000,
): Promise<T> {
  const controller = new AbortController();
  const cancel = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener("abort", cancel, { once: true });
  const timer = setTimeout(cancel, timeout);
  try {
    const response = await fetch(`${base}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined
          ? { Accept: "application/json" }
          : { Accept: "application/json", "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      credentials: "omit",
    });
    if (!response.ok) {
      const messages: Record<number, string> = {
        422: "Confira os valores informados e tente novamente.",
        429: "O limite temporário de consultas foi atingido. Aguarde um pouco e tente novamente.",
        502: "Não foi possível concluir a resposta. Tente novamente em instantes.",
        503: "Este recurso está indisponível no momento. Tente novamente em instantes.",
        504: "A consulta demorou mais que o esperado. Tente novamente em instantes.",
      };
      throw new ApiError(
        response.status,
        messages[response.status] || "Não foi possível concluir a solicitação.",
      );
    }
    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError(502, "Não foi possível ler a resposta do serviço.");
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted)
      throw new ApiError(
        504,
        "A consulta foi interrompida ou demorou mais que o esperado.",
      );
    throw new ApiError(
      0,
      "Não foi possível conectar ao TaxMind. Verifique se o serviço está disponível.",
    );
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", cancel);
  }
}

export const api = {
  health: (signal?: AbortSignal) =>
    request<Health>("/health", undefined, signal, 8_000),
  sources: (signal?: AbortSignal) =>
    request<SourceInventory>("/sources", undefined, signal),
  ask: (question: string, signal?: AbortSignal) =>
    request<Answer>("/ask", { question, top_k: 5 }, signal, 100_000),
  simulate: (input: SimulationInput, signal?: AbortSignal) =>
    request<Simulation>("/simulate", input, signal),
};
