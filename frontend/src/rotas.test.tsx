import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Rotas } from "./rotas";
import type { UsuarioAtual } from "./tipos/sessao";

function servir(respostas: Record<string, [number, unknown]>) {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>((entrada) => {
      const [status, corpo] = respostas[typeof entrada === "string" ? entrada : ""] ?? [404, null];
      return Promise.resolve(new Response(JSON.stringify(corpo), { status }));
    }),
  );
}

function abrir(rota: string) {
  render(
    <MemoryRouter initialEntries={[rota]}>
      <Rotas />
    </MemoryRouter>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("CA-008: rota protegida", () => {
  it("sem sessão vai para o login e não mostra o conteúdo", async () => {
    servir({
      "/api/sessoes/atual": [
        401,
        { erro: { codigo: "NAO_AUTENTICADO", mensagem: "x", campos: [] } },
      ],
    });
    abrir("/");
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(screen.queryByText("Maria Souza")).not.toBeInTheDocument();
  });

  it("com sessão mostra o conteúdo, o usuário e o modo", async () => {
    const sessao: UsuarioAtual = {
      usuario: { id: 3, nome: "Maria Souza", login: "maria", perfil: "OPERADOR" },
      permissoes: ["CONSULTAR_OPERACAO"],
    };
    servir({
      "/api/sessoes/atual": [200, sessao],
      "/api/operacao/estado": [
        500,
        { erro: { codigo: "ERRO_INTERNO", mensagem: "x", campos: [] } },
      ],
    });
    abrir("/nao-existe");
    expect(await screen.findByText("Maria Souza")).toBeInTheDocument();
    expect(screen.getByText("MODO DESCONHECIDO")).toBeInTheDocument();
  });

  it("'/' leva à primeira tela do menu que a sessão pode usar", async () => {
    servir({
      "/api/sessoes/atual": [
        200,
        {
          usuario: { id: 1, nome: "Ana", login: "ana", perfil: "ADMINISTRADOR" },
          permissoes: ["GERENCIAR_USUARIOS"],
        },
      ],
    });
    abrir("/");
    // <Navigate> troca a rota num efeito, depois do primeiro desenho.
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Usuários" })).toHaveAttribute(
        "aria-current",
        "page",
      );
    });
  });

  it("'/' sem nenhuma tela permitida diz isso, sem texto de início", async () => {
    servir({
      "/api/sessoes/atual": [
        200,
        { usuario: { id: 1, nome: "Ana", login: "ana", perfil: "NOVO" }, permissoes: [] },
      ],
    });
    abrir("/");
    expect(
      await screen.findByText("Seu perfil não tem acesso a nenhuma tela."),
    ).toBeInTheDocument();
  });

  it("falha que não é 401 mostra o erro e não o conteúdo", async () => {
    servir({
      "/api/sessoes/atual": [
        500,
        { erro: { codigo: "ERRO_INTERNO", mensagem: "Falha.", campos: [] } },
      ],
    });
    abrir("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("Falha.");
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
    expect(screen.queryByText("Maria Souza")).not.toBeInTheDocument();
  });
});
