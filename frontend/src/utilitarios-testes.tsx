import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Outlet, Route, Routes } from "react-router";
import { vi } from "vitest";
import type { ErroApi, Lista } from "./tipos/comum";
import type { UsuarioAtual } from "./tipos/sessao";

// Apoio dos testes das telas: sessão tipada, `fetch` simulado por "MÉTODO /api/caminho?query" e render.
export const sessao = (perfil: string, permissoes: string[]): UsuarioAtual => ({
  usuario: { id: 1, nome: "Ana", login: "ana", perfil },
  permissoes,
});
export const ADMIN = sessao("ADMINISTRADOR", ["CONSULTAR_CADASTROS", "GERENCIAR_CADASTROS"]);
export const OPERADOR = sessao("OPERADOR", ["CONSULTAR_CADASTROS"]);

export const lista = <T,>(itens: T[], extra: Partial<Lista<T>> = {}): Lista<T> => ({
  itens,
  total: itens.length,
  pagina: 1,
  tamanho_pagina: 50,
  ...extra,
});
export const erro = (
  codigo: string,
  mensagem: string,
  campos: ErroApi["erro"]["campos"] = [],
): ErroApi => ({
  erro: { codigo, mensagem, campos },
});

export type Resposta = [number, unknown] | "rede";
export type Rotas = Record<string, Resposta | (() => Resposta)>;

/** `fetch` simulado por "MÉTODO /api/caminho?query". Devolve as chamadas feitas. */
export function servir(rotas: Rotas) {
  const f = vi.fn<typeof fetch>((entrada, init) => {
    const chave = `${init?.method ?? "GET"} ${typeof entrada === "string" ? entrada : ""}`;
    const r = rotas[chave];
    const resposta = typeof r === "function" ? r() : r;
    if (resposta === "rede") return Promise.reject(new TypeError("falha de rede"));
    const [status, corpo] = resposta ?? [404, erro("NAO_ENCONTRADO", "Rota não simulada.")];
    return Promise.resolve(new Response(JSON.stringify(corpo), { status }));
  });
  vi.stubGlobal("fetch", f);
  return f;
}
export const chamadas = (f: ReturnType<typeof servir>, metodo: string) =>
  f.mock.calls.filter(([, init]) => (init?.method ?? "GET") === metodo);

export function abrir(
  rota: string,
  caminho: string,
  pagina: ReactElement,
  quem: UsuarioAtual = ADMIN,
) {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route element={<Outlet context={quem} />}>
          <Route path={caminho} element={pagina} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}
