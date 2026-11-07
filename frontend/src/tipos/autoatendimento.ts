// Contrato da API de autoatendimento: spec 013 §5. Sem sessão; nunca devolve dado de cadastro.
import type { TipoOperacao } from "./agendamentos";

export interface AgendamentoAutoatendimentoCriacao {
  placa: string;
  /** 11 dígitos. */
  cpf: string;
  tipo_operacao: TipoOperacao;
  produto_id: number;
  data_prevista: string;
  faixa_horario_id?: number | null;
  /** Obrigatório em DESCARGA, proibido em CARGA (§6.4). */
  codigo_nota?: string;
}

/** Resposta 201 (§5.1). */
export interface AgendamentoAutoatendimento {
  agendamento_id: number;
  tipo_operacao: TipoOperacao;
  data_prevista: string;
  faixa_hora_inicio: string;
  faixa_hora_fim: string;
}

export interface ProdutoAutoatendimento {
  id: number;
  codigo: string;
  descricao: string;
}

export interface FiltrosProdutosAutoatendimento {
  busca?: string;
}
