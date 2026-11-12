export const money = (value: string) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value));

export const percent = (value: string) =>
  new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 4,
  }).format(Number(value)) + "%";

export function accessDate(value: string | null) {
  if (!value || Number.isNaN(Date.parse(value))) return "Data não disponível";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export function officialUrl(value: string): string | undefined {
  try {
    const url = new URL(value);
    if (
      url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      (url.hostname.endsWith(".gov.br") || url.hostname.endsWith(".leg.br"))
    )
      return url.href;
  } catch {
    /* Uma URL inválida não se torna um link na interface. */
  }
  return undefined;
}

export function decimalInput(
  value: string,
  places: number,
  max: number,
): string | null {
  const text = value.trim();
  if (!new RegExp(`^\\d+(?:[.,]\\d{1,${places}})?$`).test(text)) return null;
  const normalized = text.replace(",", ".");
  return Number.isFinite(Number(normalized)) && Number(normalized) <= max
    ? normalized
    : null;
}

export function sourceLabel(id: string, fallback: string): string {
  return (
    (
      {
        "rfb-entenda": "Entenda a reforma",
        "rfb-comunicado-2026": "Orientações para 2026",
        "lc214-atualizada": "Lei Complementar 214/2025",
      } as Record<string, string>
    )[id] || fallback
  );
}

export function publisher(id: string): string {
  return id === "lc214-atualizada"
    ? "Câmara dos Deputados"
    : id.startsWith("rfb-")
      ? "Receita Federal"
      : "Documento público";
}
