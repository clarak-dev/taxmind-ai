import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../src/api";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("cliente da API", () => {
  it("envia a pergunta somente à API do projeto, sem credencial do provedor", async () => {
    const fetch = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ status: "abstained" }), { status: 200 }),
      );
    vi.stubGlobal("fetch", fetch);
    await api.ask("Pergunta de teste");
    const [url, options] = fetch.mock.calls[0]!;
    expect(url).toBe("/api/ask");
    expect(JSON.parse(options.body)).toEqual({
      question: "Pergunta de teste",
      top_k: 5,
    });
    expect(options.headers.Authorization).toBeUndefined();
    expect(options.credentials).toBe("omit");
  });
  it("distingue limite de consultas e não exibe detalhes internos do servidor", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":"private upstream detail"}', { status: 429 }),
        ),
    );
    await expect(api.ask("Pergunta de teste")).rejects.toMatchObject({
      status: 429,
      message: expect.stringContaining("limite temporário"),
    });
  });
  it("trata resposta não JSON como erro, sem considerá-la uma resposta do assistente", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("<html>not API</html>", { status: 200 }),
        ),
    );
    await expect(api.health()).rejects.toMatchObject({ status: 502 });
  });
  it("distingue falha de conexão de falta de evidência", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("fetch failed")),
    );
    await expect(api.sources()).rejects.toMatchObject({ status: 0 });
  });
  it("encerra a espera no timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url, options: RequestInit) =>
          new Promise((_resolve, reject) => {
            options.signal?.addEventListener("abort", () =>
              reject(new DOMException("Aborted", "AbortError")),
            );
          }),
      ),
    );
    const pending = expect(api.health()).rejects.toMatchObject({ status: 504 });
    await vi.advanceTimersByTimeAsync(8_000);
    await pending;
  });
});
