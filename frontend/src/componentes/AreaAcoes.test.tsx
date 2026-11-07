import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AreaAcoes } from "./AreaAcoes";
import { Botao } from "./Botao";

function desenhar(bloqueada: boolean) {
  return (
    <AreaAcoes bloqueada={bloqueada}>
      <Botao variante="acao">Tentar novamente</Botao>
      <Botao>Cancelar pesagem</Botao>
    </AreaAcoes>
  );
}

describe("CA-007: área de ações", () => {
  it("bloqueada desabilita todos os botões e mostra a faixa", () => {
    const { rerender } = render(desenhar(true));
    for (const botao of screen.getAllByRole("button")) expect(botao).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent("Tela desatualizada");

    rerender(desenhar(false));
    for (const botao of screen.getAllByRole("button")) expect(botao).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
