import type { Lista, Paginacao } from "../tipos/comum";
import type {
  CameraDiagnostico,
  CenariosSimuladores,
  ChegadaSimulada,
  EstadoDispositivosDiagnostico,
  ExclusaoImagemCorpo,
  FiltrosLeiturasPlaca,
  ImagemDecisao,
  LeituraPlacaDetalhe,
} from "../tipos/diagnostico";
import type { LeituraPlaca } from "../tipos/operacao";
import { comQuery, requisitar, requisitarImagem } from "./cliente-api";

// Spec 011 §4.
export const listarLeiturasPlaca = (filtros: FiltrosLeiturasPlaca & Paginacao = {}) =>
  requisitar<Lista<LeituraPlaca>>("GET", comQuery("/leituras-placa", { ...filtros }));

export const obterLeituraPlaca = (id: number) =>
  requisitar<LeituraPlacaDetalhe>("GET", `/leituras-placa/${String(id)}`);

export const obterImagemDecisao = (id: number) =>
  requisitar<ImagemDecisao>("GET", `/imagens-decisao/${String(id)}`);

export const obterConteudoImagemDecisao = (id: number) =>
  requisitarImagem(`/imagens-decisao/${String(id)}/conteudo`);

export const excluirImagemDecisao = (id: number, corpo: ExclusaoImagemCorpo) =>
  requisitar<ImagemDecisao>("POST", `/imagens-decisao/${String(id)}/excluir`, corpo);

/** Imagem atual; pedida a cada `intervalo_imagem_ms` só com a tela aberta (§6.3). */
export const obterImagemAtual = (camera: CameraDiagnostico) =>
  requisitarImagem(`/cameras/${camera}/imagem-atual`);

export const obterDispositivos = () =>
  requisitar<EstadoDispositivosDiagnostico>("GET", "/dispositivos");

export const obterSimuladores = () => requisitar<CenariosSimuladores>("GET", "/simuladores");

/** Responde 202 com os cenários; a decisão chega pelo evento `leitura_placa` (§6.4). */
export const simularChegada = (corpo: ChegadaSimulada) =>
  requisitar<CenariosSimuladores>("POST", "/simuladores/chegadas", corpo);

// Corpos da troca de cenário (§6.4): o mesmo objeto do item na §5.5.
export const trocarCenarioBalanca = (corpo: CenariosSimuladores["balanca"]) =>
  requisitar<CenariosSimuladores>("POST", "/simuladores/balanca", corpo);

export const trocarCenarioCancela = (
  cancela: "entrada" | "saida",
  corpo: { cenario: CenariosSimuladores["cancelas"][number]["cenario"] },
) => requisitar<CenariosSimuladores>("POST", `/simuladores/cancelas/${cancela}`, corpo);

export const trocarCenarioPosicao = (corpo: CenariosSimuladores["posicao"]) =>
  requisitar<CenariosSimuladores>("POST", "/simuladores/posicao", corpo);
