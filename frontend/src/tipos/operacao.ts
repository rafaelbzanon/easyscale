// Contrato da API da operação: spec 009 §5 e §6. Situações, ações e motivos: spec 006 §5.
import type { StatusAgendamento, TipoOperacao } from "./agendamentos";

export type SituacaoPesagem =
  | "AGUARDANDO_BALANCA_INICIAL"
  | "AUTORIZADA"
  | "ENTRADA_LIBERADA"
  | "FECHANDO_ENTRADA"
  | "POSICIONADA_INICIAL"
  | "PESO_INICIAL_OK"
  | "SAIDA_INICIAL_LIBERADA"
  | "FECHANDO_SAIDA_INICIAL"
  | "EM_CARGA_DESCARGA"
  | "AGUARDANDO_BALANCA_FINAL"
  | "RETORNO_AUTORIZADO"
  | "RETORNO_LIBERADO"
  | "FECHANDO_ENTRADA_RETORNO"
  | "POSICIONADA_FINAL"
  | "PESO_FINAL_OK"
  | "SAIDA_LIBERADA"
  | "FECHANDO_SAIDA"
  | "AGUARDANDO_INTERVENCAO"
  | "FINALIZADA"
  | "CANCELADA";

export type MotivoIntervencao =
  | "CANCELA_FALHA"
  | "CANCELA_SEM_CONFIRMACAO"
  | "POSICAO_PERDIDA"
  | "TEMPO_ESGOTADO"
  | "LIQUIDO_NEGATIVO"
  | "REINICIO_INCONCLUSIVO";

export type AcaoManual =
  | "TENTAR_NOVAMENTE"
  | "CONFIRMAR_POSICAO_MANUAL"
  | "CONFIRMAR_BALANCA_VAZIA_MANUAL"
  | "LIBERAR_RETORNO_MANUAL"
  | "ACEITAR_PESO_FINAL"
  | "CANCELAR";

export type NomeCancela = "ENTRADA" | "SAIDA";
export type ComandoCancela = "ABRIR" | "FECHAR";
export type ClassificacaoPesoLiquido =
  "COM_MOVIMENTACAO" | "SEM_MOVIMENTACAO" | "NEGATIVO_FORA_TOLERANCIA";

/** §5.1. Também é o item da lista da spec 010. Pesos em texto, 3 casas. */
export interface Pesagem {
  id: number;
  versao: number;
  situacao: SituacaoPesagem;
  situacao_anterior: SituacaoPesagem | null;
  motivo_intervencao: MotivoIntervencao | null;
  comando_pendente: { comando: ComandoCancela; cancela: NomeCancela } | null;
  /** Só para mostrar botões; quem decide é o backend (S-5). */
  acoes_disponiveis: AcaoManual[];
  ocupa_balanca: boolean;
  aguarda_liberacao_balanca: boolean;
  liberacao_manual: boolean;
  agendamento_id: number;
  agendamento_status: StatusAgendamento;
  tipo_operacao: TipoOperacao;
  placa: string;
  motorista_nome: string;
  transportadora_razao_social: string | null;
  produto_descricao: string;
  data_prevista: string;
  faixa_hora_inicio: string;
  faixa_hora_fim: string;
  /** Peso aceito e registrado, não leitura (RF-014). */
  peso_inicial_kg: string | null;
  peso_inicial_em: string | null;
  peso_final_kg: string | null;
  peso_final_em: string | null;
  peso_liquido_kg: string | null;
  classificacao: ClassificacaoPesoLiquido | null;
  criado_em: string;
  atualizado_em: string;
}

export type DecisaoLeitura = "AUTORIZADA" | "RETORNO_ACEITO" | "NAO_AUTORIZADA";

/** §5.3, na ordem de precedência. */
export type MotivoNaoAutorizacao =
  | "FALHA_IMAGEM"
  | "FALHA_LEITOR"
  | "SEM_CANDIDATO"
  | "PLACA_INVALIDA"
  | "AMBIGUA"
  | "CONFIANCA_BAIXA"
  | "VEICULO_NAO_CADASTRADO"
  | "VEICULO_INATIVO"
  | "OPERACAO_JA_ABERTA"
  | "SEM_AGENDAMENTO"
  | "AGENDAMENTO_AMBIGUO"
  | "MOTORISTA_INATIVO"
  | "ANTES_DA_FAIXA";

/** §5.2. */
export interface LeituraPlaca {
  id: number;
  decisao: DecisaoLeitura;
  motivo: MotivoNaoAutorizacao | null;
  placa_lida: string | null;
  placa_normalizada: string | null;
  /** De 0 a 1, 3 casas, em texto. */
  confianca: string | null;
  pesagem_id: number | null;
  agendamento_id: number | null;
  imagem_id: number | null;
  capturada_em: string;
  decidida_em: string;
}

export type ModoDispositivo = "SIMULADO" | "REAL";

export interface EstadoBalanca {
  modo: ModoDispositivo;
  comunicacao: "OK" | "FALHA" | "DESCONHECIDO";
  motivo_falha: "SEM_RESPOSTA" | "QUADRO_CORROMPIDO" | "DESCONECTADA" | null;
  comunicacao_em: string | null;
  /** Leitura recebida, não peso aceito (ADR-0005 §4.7). */
  ultima_leitura: { peso_kg: string; lida_em: string } | null;
  avaliacao_peso: {
    aceito: boolean;
    motivo_rejeicao:
      | "LEITURA_INVALIDA"
      | "FORA_DE_FAIXA"
      | "LEITURAS_INSUFICIENTES"
      | "INSTAVEL"
      | "FORA_DE_ORDEM"
      | null;
    avaliada_em: string;
  } | null;
}

export interface EstadoCancela {
  cancela: NomeCancela;
  modo: ModoDispositivo;
  estado: "ABERTA" | "FECHADA" | "DESCONHECIDO";
  estado_em: string | null;
  ultimo_comando: {
    comando: ComandoCancela;
    resultado: "CONFIRMADO" | "FALHA" | "SEM_CONFIRMACAO";
    tentativas: number;
    concluido_em: string;
    pesagem_id: number | null;
  } | null;
}

export interface EstadoPosicao {
  modo: ModoDispositivo;
  resultado: "CONFIRMADA" | "AUSENTE" | "INCONCLUSIVA" | null;
  capturada_em: string | null;
  analisada_em: string | null;
}

export interface EstadoIdentificacao {
  modo: ModoDispositivo;
  resultado: "OK" | "FALHA_IMAGEM" | "FALHA_LEITOR" | null;
  analisada_em: string | null;
}

/** §5.4. Também usado na spec 011. */
export interface EstadoDispositivos {
  balanca: EstadoBalanca;
  /** Sempre duas, ENTRADA e SAIDA, nesta ordem. */
  cancelas: [EstadoCancela, EstadoCancela];
  posicao: EstadoPosicao;
  identificacao: EstadoIdentificacao;
}

/** §5.6. */
export interface LiberacaoCaminhao {
  pesagem_id: number;
  etapa:
    | "PENDENTE"
    | "ABRINDO_SAIDA"
    | "AGUARDANDO_BALANCA_VAZIA"
    | "FECHANDO_SAIDA"
    | "CONCLUIDA"
    | "FALHOU";
  motivo_falha: "CANCELA_FALHA" | "CANCELA_SEM_CONFIRMACAO" | "TEMPO_ESGOTADO" | null;
  pedido_por: number | null;
  pedido_por_nome: string | null;
  motivo: string | null;
  pedida_em: string | null;
  atualizada_em: string;
}

/** GET /api/operacao/estado (§5.5). */
export interface EstadoOperacao {
  gerado_em: string;
  tempo_real: { intervalo_heartbeat_ms: number; limite_sem_heartbeat_ms: number };
  pesagens_abertas: Pesagem[];
  liberacoes_caminhao: LiberacaoCaminhao[];
  ultima_leitura_placa: LeituraPlaca | null;
  dispositivos: EstadoDispositivos;
}

/** `event` → `data` do canal SSE (§6.1). */
export interface EventosOperacao {
  pesagem: Pesagem;
  leitura_placa: LeituraPlaca;
  peso_lido: { peso_kg: string; lida_em: string };
  balanca: EstadoBalanca;
  cancela: EstadoCancela;
  posicao: EstadoPosicao;
  identificacao: EstadoIdentificacao;
  liberacao_caminhao: LiberacaoCaminhao;
  heartbeat: { enviado_em: string };
}

/** Corpo das ações sobre uma pesagem (§6.3). */
export interface AcaoPesagemCorpo {
  versao: number;
  motivo: string;
}

/** Corpo da liberação manual de entrada (§6.5). */
export interface LiberacaoEntradaCorpo {
  agendamento_id: number;
  motivo: string;
}

/** Corpo da liberação de caminhão cancelado (§6.6). */
export interface LiberacaoCaminhaoCorpo {
  motivo: string;
}

/** Códigos de `campos[].codigo` nos 409 das ações (§6.4). */
export type CodigoCampoOperacao =
  | "VERSAO_DESATUALIZADA"
  | "TRANSICAO_REJEITADA"
  | "OPERACAO_NAO_OCUPA_BALANCA"
  | "LIBERACAO_EM_CURSO"
  | "LEITURA_DESATUALIZADA"
  | "LEITURA_NAO_LIBERAVEL"
  | "MOTIVO_NAO_SUBSTITUIVEL"
  | "VEICULO_INATIVO"
  | "MOTORISTA_INATIVO"
  | "OPERACAO_JA_ABERTA"
  | "SEM_AGENDAMENTO";
