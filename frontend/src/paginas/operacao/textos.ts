// Textos de interface dos valores das specs 006 e 009. Valor desconhecido aparece como veio.
import type { TipoEstado } from "../../componentes/SimboloEstado";
import type { StatusAgendamento } from "../../tipos/agendamentos";
import type {
  AcaoManual,
  EstadoBalanca,
  EstadoCancela,
  EstadoIdentificacao,
  EstadoPosicao,
  LiberacaoCaminhao,
  MotivoIntervencao,
  MotivoNaoAutorizacao,
  SituacaoPesagem,
} from "../../tipos/operacao";

export const SITUACAO: Record<SituacaoPesagem, string> = {
  AGUARDANDO_BALANCA_INICIAL: "Aguardando balança (pesagem inicial)",
  AUTORIZADA: "Autorizada",
  ENTRADA_LIBERADA: "Entrada liberada",
  FECHANDO_ENTRADA: "Fechando entrada",
  POSICIONADA_INICIAL: "Na balança (pesagem inicial)",
  PESO_INICIAL_OK: "Peso inicial registrado",
  SAIDA_INICIAL_LIBERADA: "Saída liberada (após pesagem inicial)",
  FECHANDO_SAIDA_INICIAL: "Fechando saída (após pesagem inicial)",
  EM_CARGA_DESCARGA: "Em carga ou descarga",
  AGUARDANDO_BALANCA_FINAL: "Aguardando balança (pesagem final)",
  RETORNO_AUTORIZADO: "Retorno autorizado",
  RETORNO_LIBERADO: "Retorno liberado",
  FECHANDO_ENTRADA_RETORNO: "Fechando entrada (retorno)",
  POSICIONADA_FINAL: "Na balança (pesagem final)",
  PESO_FINAL_OK: "Peso final registrado",
  SAIDA_LIBERADA: "Saída liberada",
  FECHANDO_SAIDA: "Fechando saída",
  AGUARDANDO_INTERVENCAO: "Aguardando intervenção",
  FINALIZADA: "Finalizada",
  CANCELADA: "Cancelada",
};

export const MOTIVO_INTERVENCAO: Record<MotivoIntervencao, string> = {
  CANCELA_FALHA: "Falha da cancela",
  CANCELA_SEM_CONFIRMACAO: "Cancela sem confirmação",
  POSICAO_PERDIDA: "Caminhão saiu de posição",
  TEMPO_ESGOTADO: "Tempo esgotado",
  LIQUIDO_NEGATIVO: "Peso líquido negativo fora da tolerância",
  REINICIO_INCONCLUSIVO: "Reinício sem estado seguro",
};

export const MOTIVO_NAO_AUTORIZACAO: Record<MotivoNaoAutorizacao, string> = {
  FALHA_IMAGEM: "Falha na imagem da câmera",
  FALHA_LEITOR: "Falha do leitor de placas",
  SEM_CANDIDATO: "Nenhuma placa lida",
  PLACA_INVALIDA: "Texto lido não é uma placa válida",
  AMBIGUA: "Mais de uma placa lida",
  CONFIANCA_BAIXA: "Leitura com confiança baixa",
  VEICULO_NAO_CADASTRADO: "Veículo não cadastrado",
  VEICULO_INATIVO: "Veículo inativo",
  OPERACAO_JA_ABERTA: "Veículo já tem operação aberta",
  SEM_AGENDAMENTO: "Sem agendamento para hoje",
  AGENDAMENTO_AMBIGUO: "Mais de um agendamento válido",
  MOTORISTA_INATIVO: "Motorista inativo",
  ANTES_DA_FAIXA: "Antes do horário da faixa",
};

/** Rótulo, o que a ação faz e a permissão exigida (spec 022 §3.5; ADR-0004 §4.3). */
export const ACAO: Record<AcaoManual, { rotulo: string; efeito: string; permissao: string }> = {
  TENTAR_NOVAMENTE: {
    rotulo: "Tentar novamente",
    efeito: "Retoma a etapa em que a operação parou.",
    permissao: "TENTAR_NOVAMENTE",
  },
  CONFIRMAR_POSICAO_MANUAL: {
    rotulo: "Confirmar posição",
    efeito: "Confirma, no lugar da câmera, que o caminhão está na posição certa.",
    permissao: "INTERVIR_OPERACAO",
  },
  CONFIRMAR_BALANCA_VAZIA_MANUAL: {
    rotulo: "Confirmar balança vazia",
    efeito: "Confirma, no lugar da câmera, que a balança está vazia.",
    permissao: "INTERVIR_OPERACAO",
  },
  LIBERAR_RETORNO_MANUAL: {
    rotulo: "Liberar retorno",
    efeito: "Libera a volta do caminhão para a pesagem final sem a leitura da placa.",
    permissao: "INTERVIR_OPERACAO",
  },
  ACEITAR_PESO_FINAL: {
    rotulo: "Aceitar peso final",
    efeito: "Aceita o peso final mesmo com o líquido negativo fora da tolerância.",
    permissao: "INTERVIR_OPERACAO",
  },
  CANCELAR: {
    rotulo: "Cancelar pesagem",
    efeito: "Cancela a pesagem. Se o caminhão estiver na balança, ele precisa ser liberado depois.",
    permissao: "INTERVIR_OPERACAO",
  },
};

type Indicador = { tipo: TipoEstado; texto: string };

const FALHA_BALANCA = {
  SEM_RESPOSTA: "sem resposta",
  QUADRO_CORROMPIDO: "dados corrompidos",
  DESCONECTADA: "desconectada",
};
const REJEICAO_PESO = {
  LEITURA_INVALIDA: "leitura inválida",
  FORA_DE_FAIXA: "fora da faixa",
  LEITURAS_INSUFICIENTES: "leituras insuficientes",
  INSTAVEL: "instável",
  FORA_DE_ORDEM: "fora de ordem",
};

export function indicadorComunicacao(b: EstadoBalanca): Indicador {
  if (b.comunicacao === "OK") return { tipo: "ok", texto: "Comunicação OK" };
  if (b.comunicacao === "FALHA") {
    const motivo = b.motivo_falha ? `: ${FALHA_BALANCA[b.motivo_falha]}` : "";
    return { tipo: "falha", texto: `FALHA${motivo}` };
  }
  return { tipo: "atencao", texto: "DESCONHECIDO: ainda sem leitura" };
}

export function indicadorAvaliacao(b: EstadoBalanca): Indicador | null {
  const a = b.avaliacao_peso;
  if (!a) return null;
  if (a.aceito) return { tipo: "ok", texto: "Peso aceito" };
  return {
    tipo: "atencao",
    texto: `Peso rejeitado${a.motivo_rejeicao ? `: ${REJEICAO_PESO[a.motivo_rejeicao]}` : ""}`,
  };
}

export function indicadorPosicao(p: EstadoPosicao): Indicador {
  if (p.resultado === "CONFIRMADA") return { tipo: "ok", texto: "Posição confirmada" };
  if (p.resultado === "AUSENTE") return { tipo: "ok", texto: "Nenhum caminhão na balança" };
  if (p.resultado === "INCONCLUSIVA") return { tipo: "atencao", texto: "Posição INCONCLUSIVA" };
  return { tipo: "atencao", texto: "Posição DESCONHECIDA: ainda não analisada" };
}

export function indicadorIdentificacao(i: EstadoIdentificacao): Indicador {
  if (i.resultado === "OK") return { tipo: "ok", texto: "Câmera de identificação OK" };
  if (i.resultado === "FALHA_IMAGEM") return { tipo: "falha", texto: "FALHA na imagem da câmera" };
  if (i.resultado === "FALHA_LEITOR") return { tipo: "falha", texto: "FALHA do leitor de placas" };
  return { tipo: "atencao", texto: "Identificação DESCONHECIDA: ainda não analisada" };
}

/** O estado vem do sensor; DESCONHECIDO nunca vira aberta nem fechada (RN-007). */
export function indicadorCancela(c: EstadoCancela): Indicador {
  if (c.estado === "ABERTA") return { tipo: "atencao", texto: "ABERTA" };
  if (c.estado === "FECHADA") return { tipo: "ok", texto: "FECHADA" };
  return { tipo: "atencao", texto: "DESCONHECIDO" };
}

export function indicadorComando(c: EstadoCancela): Indicador | null {
  const u = c.ultimo_comando;
  if (!u) return null;
  const acao = u.comando === "ABRIR" ? "Abrir" : "Fechar";
  const tentativas = `${String(u.tentativas)} tentativa${u.tentativas === 1 ? "" : "s"}`;
  if (u.resultado === "CONFIRMADO")
    return { tipo: "ok", texto: `${acao}: confirmado (${tentativas})` };
  if (u.resultado === "FALHA") return { tipo: "falha", texto: `${acao}: FALHA (${tentativas})` };
  return { tipo: "falha", texto: `${acao}: SEM CONFIRMAÇÃO (${tentativas})` };
}

export const ETAPA_LIBERACAO: Record<LiberacaoCaminhao["etapa"], string> = {
  PENDENTE: "Aguardando pedido de liberação",
  ABRINDO_SAIDA: "Abrindo a saída",
  AGUARDANDO_BALANCA_VAZIA: "Aguardando balança vazia",
  FECHANDO_SAIDA: "Fechando a saída",
  CONCLUIDA: "Concluída",
  FALHOU: "Falhou",
};

export const FALHA_LIBERACAO: Record<NonNullable<LiberacaoCaminhao["motivo_falha"]>, string> = {
  CANCELA_FALHA: "falha da cancela",
  CANCELA_SEM_CONFIRMACAO: "cancela sem confirmação",
  TEMPO_ESGOTADO: "tempo esgotado",
};

export const STATUS_AGENDAMENTO: Record<StatusAgendamento, string> = {
  AGENDADO: "Agendado",
  EM_ANDAMENTO: "Em andamento",
  CONCLUIDO: "Concluído",
  CANCELADO: "Cancelado",
  EXPIRADO: "Expirado",
};
