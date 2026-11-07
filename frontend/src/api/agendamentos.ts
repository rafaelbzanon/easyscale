import type {
  Agendamento,
  AgendamentoAlteracao,
  AgendamentoCancelamento,
  AgendamentoCriacao,
  Disponibilidade,
  FaixaHorario,
  FaixaHorarioAlteracao,
  FaixaHorarioCriacao,
  FiltrosAgendamentos,
  FiltrosFaixasHorario,
} from "../tipos/agendamentos";
import { comQuery, recurso, requisitar } from "./cliente-api";

// Spec 008 §4. Não há DELETE.
export const agendamentos = {
  ...recurso<Agendamento, AgendamentoCriacao, AgendamentoAlteracao, FiltrosAgendamentos>(
    "/agendamentos",
  ),
  cancelar: (id: number, dados: AgendamentoCancelamento) =>
    requisitar<Agendamento>("POST", `/agendamentos/${String(id)}/cancelar`, dados),
};

export const faixasHorario = {
  ...recurso<FaixaHorario, FaixaHorarioCriacao, FaixaHorarioAlteracao, FiltrosFaixasHorario>(
    "/faixas-horario",
  ),
  /** `data` no formato `AAAA-MM-DD`. */
  disponibilidade: (data: string) =>
    requisitar<Disponibilidade>("GET", comQuery("/faixas-horario/disponibilidade", { data })),
};
