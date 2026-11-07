import { describe, expect, it } from "vitest";
import { aplicarEvento } from "./aplicar-evento";
import { depois, estadoOperacao, liberacao, pesagem, T0 } from "./dados-teste";

describe("spec 022 CA-002: ordem dos eventos pesagem", () => {
  const e = estadoOperacao();
  it("ignora versão menor ou igual", () => {
    expect(
      aplicarEvento(e, {
        tipo: "pesagem",
        dados: pesagem({ versao: 3, situacao: "PESO_INICIAL_OK" }),
      }),
    ).toBe(e);
    expect(aplicarEvento(e, { tipo: "pesagem", dados: pesagem({ versao: 2 }) })).toBe(e);
  });
  it("versão maior substitui", () => {
    const n = aplicarEvento(e, {
      tipo: "pesagem",
      dados: pesagem({ versao: 4, situacao: "PESO_INICIAL_OK" }),
    });
    expect(n.pesagens_abertas[0]?.situacao).toBe("PESO_INICIAL_OK");
  });
  it("terminal tira da fila", () => {
    const n = aplicarEvento(e, {
      tipo: "pesagem",
      dados: pesagem({ versao: 9, situacao: "FINALIZADA" }),
    });
    expect(n.pesagens_abertas).toEqual([]);
  });
  it("pesagem nova entra no fim; anterior ao estado buscado não entra", () => {
    const nova = pesagem({ id: 13, versao: 1, atualizado_em: depois(5) });
    expect(
      aplicarEvento(e, { tipo: "pesagem", dados: nova }).pesagens_abertas.map((p) => p.id),
    ).toEqual([12, 13]);
    const velha = pesagem({ id: 14, versao: 8, atualizado_em: depois(-5) });
    expect(aplicarEvento(e, { tipo: "pesagem", dados: velha })).toBe(e);
  });
});

describe("spec 022 CA-003: dispositivos e leituras mais antigos são ignorados", () => {
  const e = estadoOperacao();
  it("balança", () => {
    const velha = {
      ...e.dispositivos.balanca,
      comunicacao: "FALHA" as const,
      comunicacao_em: depois(-1),
    };
    expect(aplicarEvento(e, { tipo: "balanca", dados: velha })).toBe(e);
    const nova = { ...velha, comunicacao_em: depois(1), motivo_falha: "SEM_RESPOSTA" as const };
    expect(
      aplicarEvento(e, { tipo: "balanca", dados: nova }).dispositivos.balanca.comunicacao,
    ).toBe("FALHA");
  });
  it("cancela, pelo nome", () => {
    const [entrada] = e.dispositivos.cancelas;
    const velha = { ...entrada, estado: "ABERTA" as const, estado_em: depois(-1) };
    expect(aplicarEvento(e, { tipo: "cancela", dados: velha })).toBe(e);
    const n = aplicarEvento(e, {
      tipo: "cancela",
      dados: { ...velha, cancela: "SAIDA", estado_em: depois(2) },
    });
    expect(n.dispositivos.cancelas.map((c) => c.estado)).toEqual(["FECHADA", "ABERTA"]);
  });
  it("peso lido e posição", () => {
    expect(
      aplicarEvento(e, { tipo: "peso_lido", dados: { peso_kg: "1.000", lida_em: depois(-1) } }),
    ).toBe(e);
    const n = aplicarEvento(e, {
      tipo: "peso_lido",
      dados: { peso_kg: "1.000", lida_em: depois(1) },
    });
    expect(n.dispositivos.balanca.ultima_leitura?.peso_kg).toBe("1.000");
    expect(n.pesagens_abertas[0]?.peso_inicial_kg).toBeNull();
    const posicao = {
      ...e.dispositivos.posicao,
      resultado: "AUSENTE" as const,
      analisada_em: depois(-1),
    };
    expect(aplicarEvento(e, { tipo: "posicao", dados: posicao })).toBe(e);
  });
  it("leitura de placa", () => {
    const leitura = {
      id: 1,
      decisao: "AUTORIZADA" as const,
      motivo: null,
      placa_lida: "ABC1D23",
      placa_normalizada: "ABC1D23",
      confianca: "0.950",
      pesagem_id: 12,
      agendamento_id: 31,
      imagem_id: null,
      capturada_em: T0,
      decidida_em: depois(1),
    };
    const n = aplicarEvento(e, { tipo: "leitura_placa", dados: leitura });
    expect(
      aplicarEvento(n, { tipo: "leitura_placa", dados: { ...leitura, id: 0, decidida_em: T0 } }),
    ).toBe(n);
  });
});

describe("liberação de caminhão", () => {
  it("atualiza pela etapa e sai em CONCLUIDA", () => {
    const e = estadoOperacao({ liberacoes_caminhao: [liberacao()] });
    const a = aplicarEvento(e, {
      tipo: "liberacao_caminhao",
      dados: liberacao({ etapa: "ABRINDO_SAIDA", atualizada_em: depois(1) }),
    });
    expect(a.liberacoes_caminhao[0]?.etapa).toBe("ABRINDO_SAIDA");
    const c = aplicarEvento(a, {
      tipo: "liberacao_caminhao",
      dados: liberacao({ etapa: "CONCLUIDA", atualizada_em: depois(2) }),
    });
    expect(c.liberacoes_caminhao).toEqual([]);
  });
});
