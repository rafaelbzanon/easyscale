// Só para testes: responde "MÉTODO /api/caminho" com dados tipados pelos contratos (S-6).
import { vi } from "vitest";

type Resposta = [status: number, corpo?: unknown];
export type RotasSimuladas = Record<string, Resposta | ((corpo: unknown) => Resposta)>;

export function simularApi(rotas: RotasSimuladas) {
  const f = vi.fn<typeof fetch>((entrada, init) => {
    const metodo = init?.method ?? "GET";
    const chave = `${metodo} ${typeof entrada === "string" ? entrada : ""}`;
    const rota = rotas[chave];
    const corpo: unknown = typeof init?.body === "string" ? JSON.parse(init.body) : undefined;
    const [status, dados] = typeof rota === "function" ? rota(corpo) : (rota ?? [404, null]);
    const texto = status === 204 || dados === undefined ? null : JSON.stringify(dados);
    return Promise.resolve(new Response(texto, { status }));
  });
  vi.stubGlobal("fetch", f);
  return f;
}

export const erroApi = (codigo: string, campos: { campo: string; codigo: string }[] = []) => ({
  erro: { codigo, mensagem: `Mensagem ${codigo}.`, campos },
});

/** Corpos enviados para uma chave "MÉTODO /api/caminho". */
export const corposEnviados = (f: ReturnType<typeof simularApi>, chave: string): unknown[] =>
  f.mock.calls
    .filter(([e, i]) => `${i?.method ?? "GET"} ${typeof e === "string" ? e : ""}` === chave)
    .map(([, i]) => (typeof i?.body === "string" ? JSON.parse(i.body) : undefined) as unknown);
