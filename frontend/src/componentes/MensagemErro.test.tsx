import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ErroRequisicao } from "../api/cliente-api";
import { MensagemErro } from "./MensagemErro";

const erro = (status: number, codigo: string) =>
  new ErroRequisicao(status, { codigo, mensagem: `Mensagem ${codigo}.`, campos: [] });

describe("CA-004: mensagem de erro", () => {
  it("403 SEM_PERMISSAO mostra falta de permissão", () => {
    render(<MensagemErro erro={erro(403, "SEM_PERMISSAO")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Você não tem permissão para esta ação.");
  });

  it("403 ORIGEM_NAO_PERMITIDA não é tratado como falta de permissão", () => {
    render(<MensagemErro erro={erro(403, "ORIGEM_NAO_PERMITIDA")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Mensagem ORIGEM_NAO_PERMITIDA.");
  });

  it("sem corpo válido mostra falta de resposta", () => {
    render(<MensagemErro erro={new ErroRequisicao(0, null)} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Sem resposta válida do servidor.");
  });
});
