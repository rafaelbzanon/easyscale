// Contrato da API de diagnóstico: spec 011 §5.
import type { FormatoPlaca } from "./cadastros";
import type {
  DecisaoLeitura,
  EstadoDispositivos,
  LeituraPlaca,
  MotivoNaoAutorizacao,
} from "./operacao";

export interface Roi {
  x: number;
  y: number;
  largura: number;
  altura: number;
}

export interface FiltrosLeiturasPlaca {
  data_inicio?: string;
  data_fim?: string;
  decisao?: DecisaoLeitura;
  motivo?: MotivoNaoAutorizacao;
  pesagem_id?: number;
  placa?: string;
}

/** §5.2: a leitura com as interpretações. ROI em pixels da imagem salva. */
export interface LeituraPlacaDetalhe extends LeituraPlaca {
  formato: FormatoPlaca | null;
  correcoes: { posicao: number; lido: string; corrigido: string }[];
  origem: string;
  /** Uma por ROI, com todos os textos, inclusive os rejeitados (RF-022). */
  leituras: { roi: Roi; textos: { texto: string; confianca: string }[] }[];
}

/** §5.3. */
export interface ImagemDecisao {
  id: number;
  origem: string;
  capturada_em: string;
  roi: Roi | null;
  excluida: boolean;
  excluida_por: number | null;
  excluida_por_nome: string | null;
  excluida_em: string | null;
  motivo_exclusao: string | null;
}

export interface ExclusaoImagemCorpo {
  /** Obrigatório, não vazio, até 200 caracteres (§6.2). */
  motivo: string;
}

export type CameraDiagnostico = "identificacao" | "posicao";

/** GET /api/dispositivos (§5.4). */
export interface EstadoDispositivosDiagnostico {
  gerado_em: string;
  intervalo_imagem_ms: number;
  dispositivos: EstadoDispositivos;
}

/** §5.5. Só existe com todos os dispositivos em SIMULADO (§6.4). */
export interface CenariosSimuladores {
  balanca: {
    cenario:
      | "ESTAVEL"
      | "INSTAVEL"
      | "SEM_RESPOSTA"
      | "SEM_RESPOSTA_NA_PRIMEIRA"
      | "QUADRO_CORROMPIDO"
      | "DESCONECTADA";
    peso_kg: string | null;
    amplitude_kg: string | null;
  };
  cancelas: {
    cancela: "ENTRADA" | "SAIDA";
    cenario: "CONFIRMADO" | "CONFIRMADO_NA_SEGUNDA" | "NAO_MOVE" | "FALHA" | "SENSOR_SEM_RESPOSTA";
  }[];
  posicao: { cenario: "CONFIRMADA" | "AUSENTE" | "INCONCLUSIVA" };
  chegadas_na_fila: number;
}

/** Corpo de POST /api/simuladores/chegadas (§6.4). Lista vazia simula imagem sem texto. */
export interface ChegadaSimulada {
  textos: { texto: string; confianca: string }[];
}

/** Códigos de `campos[].codigo` desta spec. */
export type CodigoCampoDiagnostico = "IMAGEM_EXCLUIDA" | "SEM_IMAGEM";
