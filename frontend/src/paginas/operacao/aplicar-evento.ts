import type { EstadoOperacao, EventosOperacao, Pesagem } from "../../tipos/operacao";

/** Um evento do canal, já com o `data` lido (spec 009 §6.1). */
export type EventoOperacao = {
  [T in keyof EventosOperacao]: { tipo: T; dados: EventosOperacao[T] };
}[keyof EventosOperacao];

export const TIPOS_EVENTO: (keyof EventosOperacao)[] = [
  "pesagem",
  "leitura_placa",
  "peso_lido",
  "balanca",
  "cancela",
  "posicao",
  "identificacao",
  "liberacao_caminhao",
  "heartbeat",
];

const ms = (instante: string | null | undefined) =>
  instante ? Date.parse(instante) : Number.NEGATIVE_INFINITY;
const maisRecente = (...instantes: (string | null | undefined)[]) => Math.max(...instantes.map(ms));
/** Dispositivos e leituras: substitui se o instante novo não for mais velho (spec 022 §3.2). */
const naoMaisVelho = (novo: number, atual: number) => novo >= atual;

const terminal = (p: Pesagem) => p.situacao === "FINALIZADA" || p.situacao === "CANCELADA";

/**
 * Aplica um evento ao estado pelas regras de ordem da spec 009 §6.1. Função pura: o mesmo
 * evento aplicado duas vezes não muda nada, o que permite reaplicar a fila após o GET.
 */
export function aplicarEvento(e: EstadoOperacao, ev: EventoOperacao): EstadoOperacao {
  switch (ev.tipo) {
    case "pesagem": {
      const p = ev.dados;
      const atual = e.pesagens_abertas.find((x) => x.id === p.id);
      if (atual) {
        if (p.versao <= atual.versao) return e;
        const pesagens_abertas = terminal(p)
          ? e.pesagens_abertas.filter((x) => x.id !== p.id)
          : e.pesagens_abertas.map((x) => (x.id === p.id ? p : x));
        return { ...e, pesagens_abertas };
      }
      // Fora da fila: só entra se for posterior ao estado buscado; senão o GET já a cobria.
      if (terminal(p) || ms(p.atualizado_em) <= ms(e.gerado_em)) return e;
      return { ...e, pesagens_abertas: [...e.pesagens_abertas, p] };
    }
    case "leitura_placa": {
      const atual = e.ultima_leitura_placa;
      if (atual && !naoMaisVelho(ms(ev.dados.decidida_em), ms(atual.decidida_em))) return e;
      return { ...e, ultima_leitura_placa: ev.dados };
    }
    case "peso_lido": {
      const b = e.dispositivos.balanca;
      if (!naoMaisVelho(ms(ev.dados.lida_em), ms(b.ultima_leitura?.lida_em))) return e;
      return {
        ...e,
        dispositivos: { ...e.dispositivos, balanca: { ...b, ultima_leitura: ev.dados } },
      };
    }
    case "balanca": {
      const b = e.dispositivos.balanca;
      const n = ev.dados;
      const instante = (x: typeof b) =>
        maisRecente(x.comunicacao_em, x.avaliacao_peso?.avaliada_em);
      if (!naoMaisVelho(instante(n), instante(b))) return e;
      // A leitura mais nova vence: o evento balanca pode trazer uma mais velha que um peso_lido.
      const ultima_leitura =
        ms(n.ultima_leitura?.lida_em) >= ms(b.ultima_leitura?.lida_em)
          ? n.ultima_leitura
          : b.ultima_leitura;
      return { ...e, dispositivos: { ...e.dispositivos, balanca: { ...n, ultima_leitura } } };
    }
    case "cancela": {
      const n = ev.dados;
      const instante = (c: typeof n) => maisRecente(c.estado_em, c.ultimo_comando?.concluido_em);
      const [entrada, saida] = e.dispositivos.cancelas;
      const atual = n.cancela === "ENTRADA" ? entrada : saida;
      if (!naoMaisVelho(instante(n), instante(atual))) return e;
      const cancelas: EstadoOperacao["dispositivos"]["cancelas"] =
        n.cancela === "ENTRADA" ? [n, saida] : [entrada, n];
      return { ...e, dispositivos: { ...e.dispositivos, cancelas } };
    }
    case "posicao": {
      const atual = e.dispositivos.posicao;
      if (!naoMaisVelho(ms(ev.dados.analisada_em), ms(atual.analisada_em))) return e;
      return { ...e, dispositivos: { ...e.dispositivos, posicao: ev.dados } };
    }
    case "identificacao": {
      const atual = e.dispositivos.identificacao;
      if (!naoMaisVelho(ms(ev.dados.analisada_em), ms(atual.analisada_em))) return e;
      return { ...e, dispositivos: { ...e.dispositivos, identificacao: ev.dados } };
    }
    case "liberacao_caminhao": {
      const n = ev.dados;
      const atual = e.liberacoes_caminhao.find((x) => x.pesagem_id === n.pesagem_id);
      if (atual) {
        if (!naoMaisVelho(ms(n.atualizada_em), ms(atual.atualizada_em))) return e;
      } else if (n.etapa === "CONCLUIDA" || ms(n.atualizada_em) <= ms(e.gerado_em)) {
        return e;
      }
      const outras = e.liberacoes_caminhao.filter((x) => x.pesagem_id !== n.pesagem_id);
      const liberacoes_caminhao =
        n.etapa === "CONCLUIDA"
          ? outras
          : atual
            ? e.liberacoes_caminhao.map((x) => (x.pesagem_id === n.pesagem_id ? n : x))
            : [...outras, n];
      return { ...e, liberacoes_caminhao };
    }
    case "heartbeat":
      return e;
  }
}
