import type { Disponibilidade } from "../tipos/agendamentos";
import type {
  AgendamentoAutoatendimento,
  AgendamentoAutoatendimentoCriacao,
  FiltrosProdutosAutoatendimento,
  ProdutoAutoatendimento,
} from "../tipos/autoatendimento";
import type { Lista, Paginacao } from "../tipos/comum";
import { comQuery, requisitar } from "./cliente-api";

// Spec 013 §4. Sem sessão; só pela rede do pátio.
export const listarProdutosAutoatendimento = (
  filtros: FiltrosProdutosAutoatendimento & Paginacao = {},
) =>
  requisitar<Lista<ProdutoAutoatendimento>>(
    "GET",
    comQuery("/autoatendimento/produtos", { ...filtros }),
  );

export const disponibilidadeAutoatendimento = (data: string) =>
  requisitar<Disponibilidade>("GET", comQuery("/autoatendimento/disponibilidade", { data }));

export const criarAgendamentoAutoatendimento = (dados: AgendamentoAutoatendimentoCriacao) =>
  requisitar<AgendamentoAutoatendimento>("POST", "/autoatendimento/agendamentos", dados);
