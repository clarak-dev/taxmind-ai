import { describe, expect, it } from "vitest";
import { decimalInput, money, officialUrl, percent } from "../../src/format";

describe("entradas decimais", () => {
  it("aceita vírgula e ponto, preservando a string enviada ao cálculo", () => {
    expect(decimalInput("100,05", 2, 1e12)).toBe("100.05");
    expect(decimalInput("0.05", 2, 1e12)).toBe("0.05");
    expect(decimalInput("0,0001", 4, 100)).toBe("0.0001");
  });
  it.each(["-1", "1.000,00", "NaN", "Infinity", "1e3", "", "100.001"])(
    "rejeita valor monetário inválido: %s",
    (value) => {
      expect(decimalInput(value, 2, 1e12)).toBeNull();
    },
  );
  it("verifica os limites antes da requisição", () => {
    expect(decimalInput("100.0000", 4, 100)).toBe("100.0000");
    expect(decimalInput("100,0001", 4, 100)).toBeNull();
    expect(decimalInput("1000000000000.01", 2, 1e12)).toBeNull();
  });
});

describe("fontes e apresentação", () => {
  it("aceita somente links HTTPS de órgãos oficiais, sem credenciais na URL", () => {
    expect(officialUrl("https://www.gov.br/receitafederal")).toBe(
      "https://www.gov.br/receitafederal",
    );
    expect(officialUrl("https://www2.camara.leg.br/legin/")).toBe(
      "https://www2.camara.leg.br/legin/",
    );
    for (const url of [
      "javascript:alert(1)",
      "http://www.gov.br/",
      "https://www.gov.br.evil.example/",
      "https://secret@www.gov.br/",
      "bad url",
    ])
      expect(officialUrl(url)).toBeUndefined();
  });
  it("formata resultados monetários e percentuais no padrão brasileiro", () => {
    expect(money("-5.00").replaceAll("\u00a0", " ")).toBe("-R$ 5,00");
    expect(percent("0.05")).toBe("0,05%");
  });
});
