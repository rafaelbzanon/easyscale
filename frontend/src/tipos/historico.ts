// Contrato da API de histórico: spec 010 §5. O item da lista é a Pesagem da spec 009.
import type { TipoOperacao } from "./agendamentos";
import type {
  ClassificacaoPesoLiquido,
  ComandoCancela,
  MotivoIntervencao,
  NomeCancela,
  SituacaoPesagem,
} from "./operacao";

export interface FiltrosPesagens {
  data_inicio?: string;
  data_fim?: string;
  aberta?: boolean;
  situacao?: SituacaoPesagem;
  tipo_operacao?: TipoOperacao;
  classificacao?: ClassificacaoPesoLiquido;
  liberacao_manual?: boolean;
  placa?: string;
  agendamento_id?: number;
}

/** §5.2. Campos que não se aplicam ao `tipo` vêm null. Nunca traz placa, CPF ou imagem. */
export interface EventoPesagem {
  id: number;
  tipo: "TRANSICAO" | "TRANSICAO_REJEITADA" | "EVENTO_REGISTRADO" | "COMANDO_CANCELA";
  ocorrido_em: string;
  /** Evento da spec 006 §5.2, ação da §5.3, CRIACAO ou LIBERACAO_CAMINHAO_CANCELADO. */
  evento: string | null;
  situacao_origem: SituacaoPesagem;
  situacao_destino: SituacaoPesagem | null;
  motivo_rejeicao: string | null;
  motivo_intervencao: MotivoIntervencao | null;
  motivo_dispositivo: string | null;
  peso_kg: string | null;
  peso_liquido_kg: string | null;
  classificacao: ClassificacaoPesoLiquido | null;
  cancela: NomeCancela | null;
  comando: ComandoCancela | null;
  resultado: "CONFIRMADO" | "FALHA" | "SEM_CONFIRMACAO" | null;
  tentativas: number | null;
  responsavel: { id: number; nome: string } | null;
  motivo: string | null;
  imagem_id: number | null;
  leitura_placa_id: number | null;
}
