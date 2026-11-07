import type { TipoEstado } from "../../componentes/SimboloEstado";
import type { EventoPesagem } from "../../tipos/historico";
import type { ClassificacaoPesoLiquido, SituacaoPesagem } from "../../tipos/operacao";
import { ACAO } from "../operacao/textos";

// Spec 006 §5.2 e §5.3, mais CRIACAO e LIBERACAO_CAMINHAO_CANCELADO (spec 010 §5.2). Desconhecido: como veio.
const EVENTO: Record<string, string> = {
  ...Object.fromEntries(Object.entries(ACAO).map(([codigo, a]) => [codigo, a.rotulo])),
  CRIACAO: "Operação criada",
  LIBERACAO_CAMINHAO_CANCELADO: "Liberação de caminhão cancelado",
  BALANCA_DISPONIVEL: "Balança disponível",
  PLACA_RETORNO_ACEITA: "Placa de retorno aceita",
  CANCELA_CONFIRMADA: "Cancela confirmada",
  CANCELA_FALHA: "Falha da cancela",
  CANCELA_SEM_CONFIRMACAO: "Cancela sem confirmação",
  POSICAO_CONFIRMADA: "Posição confirmada",
  POSICAO_AUSENTE: "Nenhum caminhão na balança",
  POSICAO_INCONCLUSIVA: "Posição inconclusiva",
  PESO_ACEITO: "Peso aceito",
  PESO_REJEITADO: "Peso rejeitado",
  BALANCA_FALHA: "Falha da balança",
  TEMPO_ESGOTADO: "Tempo esgotado",
  REINICIO_INCONCLUSIVO: "Reinício sem estado seguro",
};

export const nomeEvento = (evento: string | null) => (evento ? (EVENTO[evento] ?? evento) : "—");

export const TIPO_EVENTO: Record<EventoPesagem["tipo"], string> = {
  TRANSICAO: "Transição",
  TRANSICAO_REJEITADA: "Transição rejeitada",
  EVENTO_REGISTRADO: "Registrado",
  COMANDO_CANCELA: "Comando de cancela",
};

export const CLASSIFICACAO: Record<ClassificacaoPesoLiquido, string> = {
  COM_MOVIMENTACAO: "Com movimentação",
  SEM_MOVIMENTACAO: "Sem movimentação",
  NEGATIVO_FORA_TOLERANCIA: "Negativo fora da tolerância",
};

/** Forma e palavra da situação: finalizada ok, cancelada falha, intervenção atenção, o resto em andamento. */
export function formaSituacao(s: SituacaoPesagem): TipoEstado {
  if (s === "FINALIZADA") return "ok";
  if (s === "CANCELADA") return "falha";
  if (s === "AGUARDANDO_INTERVENCAO") return "atencao";
  return "informacao";
}

export const formatarDataHora = (instante: string) => new Date(instante).toLocaleString("pt-BR");

/** Texto de um valor do contrato; valor que a tela não conhece aparece como veio. */
export const traduzir = (mapa: Readonly<Record<string, string>>, chave: string) =>
  mapa[chave] ?? chave;
