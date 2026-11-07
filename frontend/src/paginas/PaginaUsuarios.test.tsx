import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Rotas } from "../rotas";
import { corposEnviados, erroApi, simularApi, type RotasSimuladas } from "../simular-api";
import type { Lista } from "../tipos/comum";
import type { ListaPerfis, Usuario, UsuarioAtual } from "../tipos/sessao";

const admin = (permissoes = ["GERENCIAR_USUARIOS"]): UsuarioAtual => ({
  usuario: { id: 1, nome: "Ana Lima", login: "ana", perfil: "ADMINISTRADOR" },
  permissoes,
});
const usuario = (id: number, nome: string, perfil: string, ativo = true): Usuario => ({
  id,
  nome,
  login: nome.split(" ")[0]?.toLowerCase() ?? "",
  perfil,
  ativo,
  criado_em: "2026-11-07T10:00:00-03:00",
});
const LISTA: Lista<Usuario> = {
  itens: [usuario(1, "Ana Lima", "ADMINISTRADOR"), usuario(2, "Bruno Reis", "OPERADOR", false)],
  total: 2,
  pagina: 1,
  tamanho_pagina: 50,
};
const PERFIS: ListaPerfis = {
  itens: [
    { codigo: "ADMINISTRADOR", permissoes: ["GERENCIAR_USUARIOS"] },
    { codigo: "OPERADOR", permissoes: ["CONSULTAR_OPERACAO"] },
  ],
};

function abrir(rotas: RotasSimuladas, sessao = admin()) {
  const f = simularApi({
    "GET /api/sessoes/atual": [200, sessao],
    "GET /api/usuarios?pagina=1": [200, LISTA],
    "GET /api/perfis": [200, PERFIS],
    ...rotas,
  });
  render(
    <MemoryRouter initialEntries={["/usuarios"]}>
      <Rotas />
    </MemoryRouter>,
  );
  return f;
}

afterEach(() => vi.unstubAllGlobals());

describe("spec 017: usuários", () => {
  it("CA-004: o item Usuários aparece só com GERENCIAR_USUARIOS", async () => {
    abrir({});
    const menu = await screen.findByRole("navigation", { name: "Principal" });
    expect(within(menu).getByRole("link", { name: "Usuários" })).toBeInTheDocument();
  });

  it("CA-004: sem a permissão, o item não aparece", async () => {
    abrir(
      { "GET /api/usuarios?pagina=1": [403, erroApi("SEM_PERMISSAO")] },
      admin(["CONSULTAR_OPERACAO"]),
    );
    const menu = await screen.findByRole("navigation", { name: "Principal" });
    expect(within(menu).queryByRole("link", { name: "Usuários" })).not.toBeInTheDocument();
  });

  it("CA-005: a lista mostra nome, login, perfil legível e situação", async () => {
    abrir({});
    const linha = (await screen.findByText("Bruno Reis")).closest("tr");
    if (!linha) throw new Error("linha ausente");
    expect(within(linha).getByText("bruno")).toBeInTheDocument();
    expect(within(linha).getByText("Operador")).toBeInTheDocument();
    expect(within(linha).getByText("Inativo")).toBeInTheDocument();
  });

  it("CA-006: criar envia os quatro campos; login repetido mostra a mensagem no campo", async () => {
    const f = abrir({
      "POST /api/usuarios": [409, erroApi("CONFLITO", [{ campo: "login", codigo: "CONFLITO" }])],
    });
    const u = userEvent.setup();
    await u.type(await screen.findByLabelText("Nome"), "Carla Dias");
    await u.type(screen.getByLabelText("Login"), "carla");
    await u.selectOptions(screen.getByLabelText("Perfil"), "OPERADOR");
    await u.type(screen.getByLabelText("Senha"), "s3nha");
    await u.click(screen.getByRole("button", { name: "Criar usuário" }));
    expect(await screen.findByText("Já existe um usuário com esse login.")).toBeInTheDocument();
    expect(screen.queryByText("Mensagem CONFLITO.")).not.toBeInTheDocument();
    expect(corposEnviados(f, "POST /api/usuarios")).toEqual([
      { nome: "Carla Dias", login: "carla", perfil: "OPERADOR", senha: "s3nha" },
    ]);
  });

  it("CA-007: desativar só envia depois da confirmação; PROPRIO_USUARIO mostra a mensagem", async () => {
    const f = abrir({
      "PATCH /api/usuarios/1": [
        409,
        erroApi("CONFLITO", [{ campo: "id", codigo: "PROPRIO_USUARIO" }]),
      ],
    });
    const u = userEvent.setup();
    const linha = (await screen.findByText("Ana Lima", { selector: "td" })).closest("tr");
    if (!linha) throw new Error("linha ausente");
    await u.click(within(linha).getByRole("button", { name: "Desativar" }));
    expect(corposEnviados(f, "PATCH /api/usuarios/1")).toEqual([]);
    await u.click(screen.getByRole("button", { name: "Confirmar desativação" }));
    expect(
      await screen.findByText("Você não pode desativar o próprio usuário."),
    ).toBeInTheDocument();
    expect(corposEnviados(f, "PATCH /api/usuarios/1")).toEqual([{ ativo: false }]);
    expect(screen.queryByRole("button", { name: "Confirmar desativação" })).not.toBeInTheDocument();
  });

  it("CA-008: redefinir envia a nova senha e confirma", async () => {
    const f = abrir({ "POST /api/usuarios/2/redefinir-senha": [204] });
    const u = userEvent.setup();
    const linha = (await screen.findByText("Bruno Reis")).closest("tr");
    if (!linha) throw new Error("linha ausente");
    await u.click(within(linha).getByRole("button", { name: "Redefinir senha" }));
    await u.type(screen.getByLabelText("Nova senha de Bruno Reis"), "nova123");
    await u.click(screen.getByRole("button", { name: "Confirmar" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Senha redefinida.");
    expect(corposEnviados(f, "POST /api/usuarios/2/redefinir-senha")).toEqual([
      { nova_senha: "nova123" },
    ]);
  });

  it("CA-009: 403 mostra falta de permissão e nenhuma linha", async () => {
    abrir({ "GET /api/usuarios?pagina=1": [403, erroApi("SEM_PERMISSAO")] });
    expect(await screen.findByText("Você não tem permissão para esta ação.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
