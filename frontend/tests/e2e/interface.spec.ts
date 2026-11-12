import { expect, test } from "@playwright/test";

// Fixtures de contrato: não representam respostas ou métricas de um LLM real.
const inventory = {
  index_status: "validated",
  scope: {
    description: "Fixture técnica",
    sources: { fixture: { mode: "full_text" } },
  },
  sources: [
    {
      id: "fixture",
      title: "Documento de teste",
      url: "https://www.gov.br/fixture",
      collected: true,
      accessed_at: "2026-11-11T12:00:00Z",
      indexed_chunks: 1,
      legal_validity: "Fixture técnica, sem validade jurídica.",
    },
  ],
};
const answer = {
  question: "Pergunta de teste",
  status: "answered",
  answer: "Resposta técnica de teste. [1]",
  claims: [{ text: "Resposta técnica de teste.", citation_ids: [1] }],
  citations: [
    {
      id: 1,
      chunk_id: "fixture",
      source_id: "fixture",
      title: "Documento de teste",
      url: "https://www.gov.br/fixture",
      section: "Seção técnica",
      quote: "Trecho técnico para testar a apresentação da evidência.",
      accessed_at: "2026-11-11T12:00:00Z",
      temporal_scope: "Teste",
      legal_validity: "Fixture sem validade jurídica.",
      start_char: 0,
      end_char: 55,
    },
  ],
  reason: "supported",
  provider: "fixture",
  model: "fixture",
  prompt_version: "fixture",
  index_generation: "fixture",
  latency_ms: 1,
  notice: "Fixture",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: { status: "ok", version: "fixture", rag_status: "configured" },
    }),
  );
  await page.route("**/api/sources", (route) =>
    route.fulfill({ json: inventory }),
  );
});

test("consulta, espera e abertura da fonte citada", async ({ page }) => {
  let question = "";
  await page.route("**/api/ask", async (route) => {
    question = route.request().postDataJSON().question;
    expect(route.request().headers()["authorization"]).toBeUndefined();
    await new Promise((resolve) => setTimeout(resolve, 300));
    await route.fulfill({ json: answer });
  });
  await page.goto("/");
  await page.getByRole("button", { name: /Conheça a CBS/ }).click();
  await page.getByRole("button", { name: "Consultar documentos" }).click();
  await expect(
    page.getByText("Consultando os documentos", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Resposta técnica de teste.", { exact: false }).first(),
  ).toBeVisible();
  expect(question).toBe("O que é a CBS e de quem é sua competência?");
  await page.getByRole("button", { name: "Ver fonte 1", exact: true }).click();
  await expect(page.getByText(answer.citations[0]!.quote)).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Abrir documento", exact: false }),
  ).toHaveAttribute("href", "https://www.gov.br/fixture");
});

test("abstenção aparece sem uma resposta citada inventada", async ({
  page,
}) => {
  await page.route("**/api/ask", (route) =>
    route.fulfill({
      json: {
        ...answer,
        status: "abstained",
        answer:
          "Não encontrei evidências suficientes nos documentos disponíveis para responder com segurança.",
        claims: [],
        citations: [],
      },
    }),
  );
  await page.goto("/");
  await page.getByLabel("Qual é a sua dúvida?").fill("Pergunta fora do escopo");
  await page.getByRole("button", { name: "Consultar documentos" }).click();
  await expect(
    page.getByRole("heading", { name: "A evidência ainda não é suficiente" }),
  ).toBeVisible();
  await expect(page.locator(".citation-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Ver fontes e cobertura" }).click();
  await expect(
    page.getByRole("heading", { name: "Documentos oficiais" }),
  ).toBeVisible();
});

test("limite de uso permite nova tentativa explícita", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/ask", (route) => {
    calls += 1;
    return calls === 1
      ? route.fulfill({
          status: 429,
          json: { detail: "private upstream detail" },
        })
      : route.fulfill({ json: answer });
  });
  await page.goto("/");
  await page.getByLabel("Qual é a sua dúvida?").fill("Pergunta de teste");
  await page.getByRole("button", { name: "Consultar documentos" }).click();
  await expect(page.getByRole("alert")).toContainText("limite temporário");
  await expect(page.locator("body")).not.toContainText(
    "private upstream detail",
  );
  expect(calls).toBe(1);
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(
    page.getByRole("heading", { name: "Sua resposta", exact: true }),
  ).toBeVisible();
  expect(calls).toBe(2);
});

test("texto gerado é apresentado como texto, sem executar HTML", async ({
  page,
}) => {
  const text = '<img src=x onerror="window.fixtureExecuted=true">';
  await page.route("**/api/ask", (route) =>
    route.fulfill({
      json: { ...answer, claims: [{ text, citation_ids: [1] }] },
    }),
  );
  await page.goto("/");
  await page.getByLabel("Qual é a sua dúvida?").fill("Pergunta de teste");
  await page.getByRole("button", { name: "Consultar documentos" }).click();
  await expect(page.locator(".answer-text")).toContainText(text);
  await expect(page.locator(".answer-text img")).toHaveCount(0);
});

test("simulador valida vírgula decimal e apresenta somente resultados da API", async ({
  page,
}) => {
  let calls = 0;
  await page.route("**/api/simulate", (route) => {
    calls += 1;
    expect(route.request().postDataJSON()).toEqual({
      base_amount: "100.00",
      current_rate_percent: "10",
      proposed_rate_percent: "15",
    });
    return route.fulfill({
      json: {
        currency: "BRL",
        base_amount: "100.00",
        current: {
          rate_percent: "10",
          tax_amount: "10.00",
          total_amount: "110.00",
        },
        proposed: {
          rate_percent: "15",
          tax_amount: "15.00",
          total_amount: "115.00",
        },
        tax_difference: "5.00",
        formula: "Fixture",
        rounding: "Fixture",
        disclaimer: "Fixture",
      },
    });
  });
  await page.goto("/#simulador");
  await expect(page.getByText("R$ 115,00")).toHaveCount(0);
  await page.getByLabel("Valor sem tributo").fill("-1");
  await page.getByRole("button", { name: "Comparar cenários" }).click();
  await expect(
    page.getByText("Informe um valor entre zero", { exact: false }),
  ).toBeVisible();
  expect(calls).toBe(0);
  await page.getByLabel("Valor sem tributo").fill("100,00");
  await page.getByRole("button", { name: "Comparar cenários" }).click();
  await expect(page.getByText("R$ 115,00")).toBeVisible();
  await expect(page.locator(".difference")).toContainText("R$ 5,00");
  await page.getByLabel("Taxa do cenário B").fill("12");
  await expect(
    page.getByText("Você alterou os parâmetros.", { exact: false }),
  ).toBeVisible();
});

test("navegação e fontes funcionam por link direto sem rolagem horizontal", async ({
  page,
}) => {
  for (const view of ["assistente", "simulador", "fontes"]) {
    await page.goto(`/#${view}`);
    await expect(
      page.getByRole("navigation").getByRole("link", {
        name: new RegExp(
          view === "fontes"
            ? "Fontes"
            : view === "simulador"
              ? "Simulador"
              : "Assistente",
        ),
      }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await expect(
    page.getByRole("link", { name: "Abrir fonte oficial" }),
  ).toHaveAttribute("href", "https://www.gov.br/fixture");
});

test("fontes continuam acessíveis quando o assistente não está configurado", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: { status: "ok", version: "fixture", rag_status: "not_configured" },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByText("O assistente está indisponível no momento.", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Explorar as fontes" }).click();
  await expect(
    page.getByRole("heading", { name: "Documentos oficiais" }),
  ).toBeVisible();
});

test("navegar preserva parâmetros e o atalho de conteúdo mantém a área atual", async ({
  page,
}) => {
  await page.goto("/#simulador");
  await page.getByLabel("Valor sem tributo").fill("250,50");
  await page
    .getByRole("navigation")
    .getByRole("link", { name: /Fontes/ })
    .click();
  await expect(
    page.getByRole("heading", { name: "Documentos oficiais" }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: /Simulador/ })
    .click();
  await expect(page.getByLabel("Valor sem tributo")).toHaveValue("250,50");
  const skip = page.getByRole("link", { name: "Pular para o conteúdo" });
  await skip.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main-content")).toBeFocused();
  await expect(page).toHaveURL(/#simulador$/);
});
