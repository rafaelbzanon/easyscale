import type {
  AcaoManual,
  AcaoPesagemCorpo,
  EstadoOperacao,
  LiberacaoCaminhaoCorpo,
  LiberacaoEntradaCorpo,
  Pesagem,
} from "../tipos/operacao";
import { requisitar } from "./cliente-api";

// Spec 009 §4.

/** Canal SSE, só leitura (§6.1). O consumo fica na FE-303. */
export const URL_EVENTOS_OPERACAO = "/api/operacao/eventos";

export const obterEstadoOperacao = () => requisitar<EstadoOperacao>("GET", "/operacao/estado");
export const obterPesagem = (id: number) => requisitar<Pesagem>("GET", `/pesagens/${String(id)}`);

/** Rota de cada ação de `acoes_disponiveis` (§4.2). */
export const ROTAS_ACAO = {
  TENTAR_NOVAMENTE: "tentar-novamente",
  CONFIRMAR_POSICAO_MANUAL: "confirmar-posicao",
  CONFIRMAR_BALANCA_VAZIA_MANUAL: "confirmar-balanca-vazia",
  LIBERAR_RETORNO_MANUAL: "liberar-retorno",
  ACEITAR_PESO_FINAL: "aceitar-peso-final",
  CANCELAR: "cancelar",
} as const satisfies Record<AcaoManual, string>;

/** 200 quer dizer transição gravada, não cancela movida (§6.3). */
export const executarAcao = (pesagemId: number, acao: AcaoManual, corpo: AcaoPesagemCorpo) =>
  requisitar<Pesagem>("POST", `/pesagens/${String(pesagemId)}/${ROTAS_ACAO[acao]}`, corpo);

export const liberarCaminhao = (pesagemId: number, corpo: LiberacaoCaminhaoCorpo) =>
  requisitar<Pesagem>("POST", `/pesagens/${String(pesagemId)}/liberar-caminhao`, corpo);

/** Responde 201 com a nova Pesagem (§6.5). */
export const liberarEntrada = (leituraPlacaId: number, corpo: LiberacaoEntradaCorpo) =>
  requisitar<Pesagem>("POST", `/leituras-placa/${String(leituraPlacaId)}/liberar-entrada`, corpo);
