import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EstadoDispositivos, ModoDispositivo } from "../tipos/operacao";
import { PlacaModo, resumirModo } from "./PlacaModo";

const EM = "2026-11-07T10:00:00-03:00";

// Dados simulados tipados pela spec 009 §5.4 (S-6).
function estado(
  balanca: ModoDispositivo,
  entrada: ModoDispositivo = "SIMULADO",
  saida: ModoDispositivo = "SIMULADO",
): { dispositivos: EstadoDispositivos } {
  const cancela = (nome: "ENTRADA" | "SAIDA", modo: ModoDispositivo) => ({
    cancela: nome,
    modo,
    estado: "FECHADA" as const,
    estado_em: EM,
    ultimo_comando: null,
  });
  return {
    dispositivos: {
      balanca: {
        modo: balanca,
        comunicacao: "OK",
        motivo_falha: null,
        comunicacao_em: EM,
        ultima_leitura: null,
        avaliacao_peso: null,
      },
      cancelas: [cancela("ENTRADA", entrada), cancela("SAIDA", saida)],
      posicao: { modo: "SIMULADO", resultado: null, capturada_em: null, analisada_em: null },
      identificacao: { modo: "SIMULADO", resultado: null, analisada_em: null },
    },
  };
}

describe("CA-006: placa de modo", () => {
  it("todos SIMULADO mostra simulado", () => {
    render(<PlacaModo estado={estado("SIMULADO")} />);
    expect(screen.getByText("SIMULADO")).toBeInTheDocument();
  });

  it("um REAL mostra real com a lista dos dispositivos reais", () => {
    expect(resumirModo(estado("REAL", "REAL"))).toEqual({
      tipo: "REAL",
      reais: ["balança", "cancela de entrada"],
    });
    render(<PlacaModo estado={estado("SIMULADO", "SIMULADO", "REAL")} />);
    expect(screen.getByText("REAL")).toBeInTheDocument();
    expect(screen.getByText(/cancela de saída/)).toBeInTheDocument();
  });

  it.each([
    ["sem resposta", null],
    ["sem dispositivos", {}],
    ["campo modo ausente", { dispositivos: { ...estado("SIMULADO").dispositivos, posicao: {} } }],
    [
      "modo inesperado",
      { dispositivos: { ...estado("SIMULADO").dispositivos, balanca: { modo: "X" } } },
    ],
    ["uma cancela só", { dispositivos: { ...estado("SIMULADO").dispositivos, cancelas: [] } }],
  ])("%s mostra desconhecido, nunca simulado", (_caso, valor) => {
    render(<PlacaModo estado={valor} />);
    expect(screen.getByText("MODO DESCONHECIDO")).toBeInTheDocument();
    expect(screen.queryByText("SIMULADO")).not.toBeInTheDocument();
  });
});
