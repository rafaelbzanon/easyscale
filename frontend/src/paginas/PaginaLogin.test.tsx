import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Rotas } from "../rotas";
import { corposEnviados, erroApi, simularApi } from "../simular-api";
import type { UsuarioAtual } from "../tipos/sessao";

const SESSAO: UsuarioAtual = {
  usuario: { id: 1, nome: "Ana Lima", login: "ana", perfil: "ADMINISTRADOR" },
  permissoes: ["GERENCIAR_USUARIOS"],
};

async function entrarCom(login: string, senha: string) {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Rotas />
    </MemoryRouter>,
  );
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText("Login"), login);
  await usuario.type(screen.getByLabelText("Senha"), senha);
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));
}

afterEach(() => vi.unstubAllGlobals());

describe("spec 017: login", () => {
  it("CA-001: envia login e senha e vai para o início", async () => {
    const f = simularApi({
      "POST /api/sessoes": [201, SESSAO],
      "GET /api/sessoes/atual": [200, SESSAO],
    });
    await entrarCom("ana", "segredo");
    // <Navigate> troca a rota num efeito, depois do primeiro desenho.
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Usuários" })).toHaveAttribute(
        "aria-current",
        "page",
      );
    });
    expect(corposEnviados(f, "POST /api/sessoes")).toEqual([{ login: "ana", senha: "segredo" }]);
  });

  it("CA-002: credenciais inválidas mostram a mensagem, limpam a senha e ficam na tela", async () => {
    simularApi({ "POST /api/sessoes": [401, erroApi("CREDENCIAIS_INVALIDAS")] });
    await entrarCom("ana", "errada");
    expect(await screen.findByRole("alert")).toHaveTextContent("Login ou senha incorretos.");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
    expect(screen.getByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("CA-003: login bloqueado mostra a mensagem de bloqueio", async () => {
    simularApi({ "POST /api/sessoes": [429, erroApi("LOGIN_BLOQUEADO")] });
    await entrarCom("ana", "qualquer");
    expect(await screen.findByRole("alert")).toHaveTextContent("Login bloqueado");
  });
});
