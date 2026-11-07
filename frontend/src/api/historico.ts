import type { Lista, Paginacao } from "../tipos/comum";
import type { EventoPesagem, FiltrosPesagens } from "../tipos/historico";
import type { Pesagem } from "../tipos/operacao";
import { comQuery, requisitar } from "./cliente-api";

// Spec 010 §4. Só consulta.
export const listarPesagens = (filtros: FiltrosPesagens & Paginacao = {}) =>
  requisitar<Lista<Pesagem>>("GET", comQuery("/pesagens", { ...filtros }));

export const listarEventosPesagem = (pesagemId: number, paginacao: Paginacao = {}) =>
  requisitar<Lista<EventoPesagem>>(
    "GET",
    comQuery(`/pesagens/${String(pesagemId)}/eventos`, { ...paginacao }),
  );
