import type { ErroApi, Lista, Paginacao } from "../tipos/comum";

/** Erro de uma chamada à API. `erro` é nulo quando não houve corpo no formato da spec 007 §3.2. */
export class ErroRequisicao extends Error {
  constructor(
    readonly status: number,
    readonly erro: ErroApi["erro"] | null,
  ) {
    super(erro?.mensagem ?? "Sem resposta válida do servidor.");
    this.name = "ErroRequisicao";
  }
}

let aoNaoAutenticado: () => void = () => undefined;

/** A casca registra aqui a ida ao login (ADR-0004 §5). */
export function definirAoNaoAutenticado(acao: () => void): void {
  aoNaoAutenticado = acao;
}

function eErroApi(corpo: unknown): corpo is ErroApi {
  if (typeof corpo !== "object" || corpo === null || !("erro" in corpo)) return false;
  const erro = corpo.erro;
  return (
    typeof erro === "object" &&
    erro !== null &&
    "codigo" in erro &&
    typeof erro.codigo === "string" &&
    "mensagem" in erro &&
    typeof erro.mensagem === "string" &&
    "campos" in erro &&
    Array.isArray(erro.campos)
  );
}

type Metodo = "GET" | "POST" | "PATCH" | "DELETE";

/** Chama `/api{caminho}` na mesma origem, com o cookie de sessão (spec 012 §6.1, §6.9). */
export async function requisitar<T>(metodo: Metodo, caminho: string, corpo?: unknown): Promise<T> {
  const init: RequestInit = { method: metodo, credentials: "same-origin" };
  if (metodo !== "GET") {
    // Spec 012 §6.9: mudança de estado sempre em JSON, mesmo sem corpo útil.
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(corpo ?? {});
  }

  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, init);
  } catch {
    throw new ErroRequisicao(0, null);
  }

  if (resposta.status === 204) return undefined as T;

  const corpoResposta: unknown = await resposta.json().catch(() => null);
  if (resposta.ok) {
    if (corpoResposta === null) throw new ErroRequisicao(resposta.status, null);
    return corpoResposta as T;
  }

  throw erroDaResposta(resposta.status, corpoResposta);
}

function erroDaResposta(status: number, corpo: unknown): ErroRequisicao {
  const erro = eErroApi(corpo) ? corpo.erro : null;
  if (status === 401 && erro?.codigo === "NAO_AUTENTICADO") aoNaoAutenticado();
  return new ErroRequisicao(status, erro);
}

/** Imagem da API (spec 011): bytes no sucesso, corpo da spec 007 §3.2 no erro. */
export async function requisitarImagem(
  caminho: string,
): Promise<{ imagem: Blob; capturadaEm: string | null }> {
  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, { credentials: "same-origin" });
  } catch {
    throw new ErroRequisicao(0, null);
  }
  if (resposta.ok) {
    // Last-Modified traz o instante da captura (011 §6.3).
    return { imagem: await resposta.blob(), capturadaEm: resposta.headers.get("Last-Modified") };
  }
  const corpo: unknown = await resposta.json().catch(() => null);
  throw erroDaResposta(resposta.status, corpo);
}

type ValorQuery = string | number | boolean | undefined;

/** Monta `caminho?a=1&b=x`, sem os parâmetros ausentes. */
export function comQuery(caminho: string, parametros: Record<string, ValorQuery>): string {
  const query = new URLSearchParams();
  for (const [nome, valor] of Object.entries(parametros)) {
    if (valor !== undefined) query.set(nome, String(valor));
  }
  const texto = query.toString();
  return texto ? `${caminho}?${texto}` : caminho;
}

/** As quatro rotas de um recurso com a forma da spec 007 §4.1 (também usada na 008). */
// eslint-disable-next-line @typescript-eslint/no-unnecessary-type-parameters -- os tipos são passados por quem chama, um conjunto por recurso
export function recurso<T, Criacao, Alteracao, Filtros extends object>(caminho: string) {
  return {
    listar: (filtros: Filtros & Paginacao = {} as Filtros & Paginacao) =>
      requisitar<Lista<T>>("GET", comQuery(caminho, filtros as Record<string, ValorQuery>)),
    obter: (id: number) => requisitar<T>("GET", `${caminho}/${String(id)}`),
    criar: (dados: Criacao) => requisitar<T>("POST", caminho, dados),
    alterar: (id: number, dados: Alteracao) =>
      requisitar<T>("PATCH", `${caminho}/${String(id)}`, dados),
  };
}
