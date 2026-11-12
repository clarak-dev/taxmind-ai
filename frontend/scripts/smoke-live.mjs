import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { chromium, expect } from "@playwright/test";

const root = fileURLToPath(new URL("../../", import.meta.url));
const baseURL = process.env.TAXMIND_WEB_URL || "http://127.0.0.1:8000";
const screenshots = new URL(
  "../../.local-notes/frontend-preview/",
  import.meta.url,
);
const browser = await chromium.launch({
  channel:
    process.env.PLAYWRIGHT_CHANNEL ||
    (process.platform === "win32" ? "msedge" : undefined),
  headless: true,
});

try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  const errors = [];
  const requests = [];
  page.on("pageerror", (error) => errors.push(error.name));
  page.on("request", (request) =>
    requests.push({
      url: request.url(),
      authorization: Boolean(request.headers()["authorization"]),
    }),
  );
  const home = await page.goto(baseURL, { waitUntil: "networkidle" });
  assert.equal(home.status(), 200);
  await expect(page.locator(".connection-badge.online")).toBeVisible();
  await expect(page.locator(".reading-list a")).toHaveCount(3);
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await mkdir(screenshots, { recursive: true });
  await page.screenshot({
    path: fileURLToPath(new URL("desktop.png", screenshots)),
    fullPage: true,
  });

  const question = "A CBS é um tributo de competência de qual ente federativo?";
  await page.getByLabel("Qual é a sua dúvida?").fill(question);
  const responsePromise = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/ask",
    { timeout: 110_000 },
  );
  await page.getByRole("button", { name: "Consultar documentos" }).click();
  const response = await responsePromise;
  assert.equal(
    response.status(),
    200,
    "A consulta real deve responder HTTP 200.",
  );
  const answer = await response.json();
  assert.equal(
    answer.status,
    "answered",
    "A pergunta selecionada precisa receber resposta com fonte.",
  );
  assert(answer.citations.length > 0);
  const corpus = JSON.parse(
    await readFile(
      new URL("../../data/processed/corpus.json", import.meta.url),
      "utf8",
    ),
  );
  for (const citation of answer.citations) {
    const document = corpus.documents.find(
      (item) => item.id === citation.source_id,
    );
    assert(document);
    assert.equal(
      document.text.slice(citation.start_char, citation.end_char),
      citation.quote,
    );
    assert.equal(document.url, citation.url);
  }
  await expect(page.locator(".answer-section")).toBeVisible();
  await page
    .getByRole("button", {
      name: `Ver fonte ${answer.citations[0].id}`,
      exact: true,
    })
    .first()
    .click();
  await expect(
    page.locator(".citation-content blockquote").first(),
  ).toBeVisible();
  await page.screenshot({
    path: fileURLToPath(new URL("answer.png", screenshots)),
    fullPage: true,
  });

  await page
    .getByRole("navigation")
    .getByRole("link", { name: /Simulador/ })
    .click();
  await page.getByLabel("Valor sem tributo").fill("100,00");
  await page.getByLabel("Taxa do cenário A").fill("10");
  await page.getByLabel("Taxa do cenário B").fill("15");
  const calculationPromise = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/api/simulate",
  );
  await page.getByRole("button", { name: "Comparar cenários" }).click();
  const calculation = await calculationPromise;
  assert.equal(calculation.status(), 200);
  const simulation = await calculation.json();
  assert.equal(simulation.tax_difference, "5.00");
  await expect(page.locator(".difference")).toContainText("R$ 5,00");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: fileURLToPath(new URL("mobile.png", screenshots)),
    fullPage: true,
  });
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );

  await page
    .getByRole("navigation")
    .getByRole("link", { name: /Fontes/ })
    .click();
  await expect(page.locator(".source-document")).toHaveCount(3);
  assert(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  assert.equal(errors.length, 0);
  assert(
    requests.every(
      (request) =>
        !request.authorization &&
        new URL(request.url).hostname !== "api.groq.com",
    ),
  );
  const report = {
    checked_at: new Date().toISOString(),
    transport:
      "Browser, compiled frontend and FastAPI over loopback; real external LLM",
    browser: await browser.version(),
    checks: {
      frontend_and_api_same_origin: "passed",
      sources: "passed",
      real_answer: "passed",
      citation_offsets_in_collected_document: "passed",
      simulation: "passed",
      desktop_and_mobile_overflow: "passed",
      no_provider_credentials_in_browser_requests: "passed",
      javascript_errors: errors.length,
    },
    viewports: [
      { width: 1440, height: 1000 },
      { width: 390, height: 844 },
    ],
    answer,
    simulation,
    limitations: [
      "One public question and one hypothetical calculation; not a general quality evaluation.",
      "Same model generates and reviews claims; legal interpretation needs further review.",
    ],
  };
  await writeFile(
    new URL("../../reports/frontend-live-smoke.json", import.meta.url),
    JSON.stringify(report, null, 2),
    "utf8",
  );
  console.log(
    "Browser real: resposta com fonte, cálculo, documentos e layout aprovados.",
  );
} finally {
  await browser.close();
}
