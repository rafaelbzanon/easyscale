// Texto curto por `campos[].codigo`. Cadastros: spec 018 §11; agendamentos e faixas: spec 008 §6.10.
export const TEXTO_CODIGO: Record<string, string> = {
  PLACA_INVALIDA: "Placa inválida. A tela não troca letras por números.",
  CAMPO_INVALIDO: "Valor inválido.",
  CONFLITO: "Já existe um cadastro com este valor, ou ele está ligado a uma operação aberta.",
  DATA_NO_PASSADO: "A data já passou.",
  FAIXA_SEM_VAGA: "A faixa não tem mais vaga.",
  FAIXA_ENCERRADA: "A faixa de hoje já terminou.",
  SEM_FAIXA_DISPONIVEL: "Não há faixa com vaga nesse dia.",
  VEICULO_JA_AGENDADO: "Este veículo já tem um agendamento aberto.",
  STATUS_NAO_PERMITE: "O status do agendamento não permite esta ação.",
  CODIGO_NOTA_NAO_PERMITIDO: "Código da nota só vale em descarga.",
  FAIXA_SOBREPOSTA: "Esta faixa se sobrepõe a outra faixa ativa.",
  FAIXA_COM_AGENDAMENTOS: "Há agendamentos nesta faixa. Desative-a e crie outra.",
};

export const textoCodigo = (codigo: string) => TEXTO_CODIGO[codigo] ?? "Corrija este campo.";
