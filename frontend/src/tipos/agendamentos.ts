// Contrato da API de agendamentos e faixas de horário: spec 008 §5.

export type TipoOperacao = "CARGA" | "DESCARGA";
export type StatusAgendamento =
  "AGENDADO" | "EM_ANDAMENTO" | "CONCLUIDO" | "CANCELADO" | "EXPIRADO";
export type OrigemAgendamento = "USUARIO" | "AUTOATENDIMENTO";

export interface Agendamento {
  id: number;
  veiculo_id: number;
  motorista_id: number;
  transportadora_id: number | null;
  produto_id: number;
  tipo_operacao: TipoOperacao;
  /** Data `AAAA-MM-DD`. */
  data_prevista: string;
  faixa_horario_id: number;
  codigo_nota: string | null;
  observacao: string | null;
  status: StatusAgendamento;
  origem: OrigemAgendamento;
  criado_por: number | null;
  criado_em: string;
  cancelado_por: number | null;
  cancelado_em: string | null;
  motivo_cancelamento: string | null;
  // Resumo somente leitura do cadastro atual (§5.1). Nunca traz CPF.
  placa: string;
  motorista_nome: string;
  transportadora_razao_social: string | null;
  produto_descricao: string;
  faixa_hora_inicio: string;
  faixa_hora_fim: string;
}

export interface AgendamentoCriacao {
  veiculo_id: number;
  motorista_id: number;
  transportadora_id?: number | null;
  produto_id: number;
  tipo_operacao: TipoOperacao;
  data_prevista: string;
  /** Ausente ou null: o backend usa a primeira faixa com vaga (§6.3). */
  faixa_horario_id?: number | null;
  /** Só em DESCARGA (§6.8). */
  codigo_nota?: string | null;
  observacao?: string | null;
}

/** No PATCH, `faixa_horario_id: null` dá 422 (§6.5). */
export type AgendamentoAlteracao = Partial<Omit<AgendamentoCriacao, "faixa_horario_id">> & {
  faixa_horario_id?: number;
};

export interface AgendamentoCancelamento {
  /** Obrigatório, não vazio, até 200 caracteres (§6.5). */
  motivo: string;
}

export interface FiltrosAgendamentos {
  data_inicio?: string;
  data_fim?: string;
  status?: StatusAgendamento;
  tipo_operacao?: TipoOperacao;
  origem?: OrigemAgendamento;
  placa?: string;
}

export interface FaixaHorario {
  id: number;
  /** Hora `HH:MM`. */
  hora_inicio: string;
  hora_fim: string;
  capacidade: number;
  ativo: boolean;
}

export interface FaixaHorarioCriacao {
  hora_inicio: string;
  hora_fim: string;
  capacidade: number;
}

export type FaixaHorarioAlteracao = Partial<FaixaHorarioCriacao> & { ativo?: boolean };

export interface FiltrosFaixasHorario {
  ativo?: boolean;
}

export interface VagaFaixa {
  faixa_horario_id: number;
  hora_inicio: string;
  hora_fim: string;
  capacidade: number;
  vagas_ocupadas: number;
  vagas_livres: number;
  encerrada: boolean;
}

/** GET /api/faixas-horario/disponibilidade (§5.3); não paginada. */
export interface Disponibilidade {
  data: string;
  itens: VagaFaixa[];
}

/** Códigos de `campos[].codigo` desta spec (§6.10), além dos comuns da spec 007. */
export type CodigoCampoAgendamento =
  | "DATA_NO_PASSADO"
  | "FAIXA_SEM_VAGA"
  | "FAIXA_ENCERRADA"
  | "SEM_FAIXA_DISPONIVEL"
  | "VEICULO_JA_AGENDADO"
  | "STATUS_NAO_PERMITE"
  | "CODIGO_NOTA_NAO_PERMITIDO"
  | "FAIXA_SOBREPOSTA"
  | "FAIXA_COM_AGENDAMENTOS";
