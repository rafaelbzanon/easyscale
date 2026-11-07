import { ErroRequisicao } from "../../api/cliente-api";

export type Etapa = "tipo" | "produto" | "data" | "faixa" | "placa" | "cpf" | "nota" | "conferir";

const GERAL = "Não foi possível agendar agora. Nada foi salvo. Fale com o operador.";

/**
 * Texto fixo e passo para voltar, por falha do `POST` (spec 020 §7). Nunca repete a mensagem do
 * backend e nunca diz qual dado do cadastro falhou (RN-021, ADR-0004 §4.4 item 3).
 */
export function tratarErroEnvio(e: unknown): { texto: string; etapa: Etapa | null } {
  if (!(e instanceof ErroRequisicao)) return { texto: GERAL, etapa: null };
  if (e.status === 404 || e.erro?.codigo === "REDE_NAO_PERMITIDA") {
    return {
      texto: "O autoatendimento não está disponível aqui. Fale com o operador.",
      etapa: null,
    };
  }
  if (e.erro === null) return { texto: GERAL, etapa: null };
  const codigos = e.erro.campos.map((c) => c.codigo);
  const campos = e.erro.campos.map((c) => c.campo);
  if (e.erro.codigo === "DADOS_NAO_CONFEREM") {
    return {
      texto: "Placa ou CPF não conferem. Confira os dois ou fale com o operador.",
      etapa: "placa",
    };
  }
  if (e.erro.codigo === "AUTOATENDIMENTO_BLOQUEADO") {
    return { texto: "Este totem está bloqueado por um tempo. Fale com o operador.", etapa: null };
  }
  if (codigos.includes("CODIGO_NOTA_OBRIGATORIO")) {
    return { texto: "Informe o código da nota.", etapa: "nota" };
  }
  if (codigos.includes("DATA_NO_PASSADO")) {
    return { texto: "Essa data já passou. Escolha outra.", etapa: "data" };
  }
  if (
    ["FAIXA_SEM_VAGA", "FAIXA_ENCERRADA", "SEM_FAIXA_DISPONIVEL"].some((c) => codigos.includes(c))
  ) {
    return { texto: "Essa faixa não tem mais vaga. Escolha outra.", etapa: "faixa" };
  }
  if (codigos.includes("VEICULO_JA_AGENDADO")) {
    return {
      texto: "Este veículo já tem um agendamento aberto. Fale com o operador.",
      etapa: null,
    };
  }
  if (campos.includes("placa") || codigos.includes("PLACA_INVALIDA")) {
    return { texto: "Placa inválida. Confira as letras e os números.", etapa: "placa" };
  }
  if (campos.includes("cpf")) return { texto: "CPF inválido. Confira os números.", etapa: "cpf" };
  return { texto: GERAL, etapa: null };
}

/** Falha ao carregar produtos ou faixas. */
export function textoCarga(e: unknown): string {
  return e instanceof ErroRequisicao && (e.status === 403 || e.status === 404)
    ? "O autoatendimento não está disponível aqui. Fale com o operador."
    : "Não foi possível carregar. Tente de novo.";
}
