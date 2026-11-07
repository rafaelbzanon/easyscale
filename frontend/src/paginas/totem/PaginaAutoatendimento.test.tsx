import { cleanup, act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Disponibilidade } from "../../tipos/agendamentos";
import type { AgendamentoAutoatendimento } from "../../tipos/autoatendimento";
import { chamadas, erro, lista, servir, type Resposta, type Rotas } from "../../utilitarios-testes";
import { hoje } from "../agendamentos/formatos";
import { PaginaAutoatendimento } from "./PaginaAutoatendimento";

const HOJE = hoje();
const vaga = (id: number, ini: string, fim: string, livres: number, encerrada = false) => ({
  faixa_horario_id: id,
  hora_inicio: ini,
  hora_fim: fim,
  capacidade: 2,
  vagas_ocupadas: 2 - livres,
  vagas_livres: livres,
  encerrada,
});
const DISP: Disponibilidade = {
  data: HOJE,
  itens: [vaga(1, "08:00", "10:00", 0), vaga(2, "10:00", "12:00", 1), vaga(3, "12:00", "14:00", 2)],
};
const CRIADO: AgendamentoAutoatendimento = {
  agendamento_id: 42,
  tipo_operacao: "CARGA",
  data_prevista: HOJE,
  faixa_hora_inicio: "10:00",
  faixa_hora_fim: "12:00",
};
const URL_PRODUTOS = "GET /api/autoatendimento/produtos?pagina=1";
const URL_DISP = `GET /api/autoatendimento/disponibilidade?data=${HOJE}`;
const POST = "POST /api/autoatendimento/agendamentos";
const BASE: Rotas = {
  [URL_PRODUTOS]: [200, lista([{ id: 30, codigo: "SOJA", descricao: "Soja em grão" }])],
  [URL_DISP]: [200, DISP],
  [POST]: [201, CRIADO],
};

const botao = (nome: string) => screen.findByRole("button", { name: nome });
const tocar = async (nome: string) => {
  await userEvent.click(await botao(nome));
};
const digitar = async (rotulo: string, texto: string) => {
  await userEvent.type(await screen.findByLabelText(rotulo), texto);
};
const corpo = (f: ReturnType<typeof servir>) =>
  JSON.parse(chamadas(f, "POST")[0]?.[1]?.body as string) as Record<string, unknown>;

/** Do início até o resumo, em Carga ou Descarga. */
async function ateConferir(tipo: "Carga" | "Descarga" = "Carga") {
  await tocar(tipo);
  await tocar("Soja em grão");
  await tocar("Hoje");
  await tocar(/10:00 às 12:00/ as unknown as string);
  await digitar("Placa", "abc1d23");
  await tocar("Avançar");
  await digitar("CPF (só números)", "52998224725");
  await tocar("Avançar");
  if (tipo === "Descarga") {
    await digitar("Código da nota", "NF-9");
    await tocar("Avançar");
  }
  await screen.findByRole("heading", { name: "Confira os dados" });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("CA-001, CA-007: fluxo de Carga", () => {
  it("envia o escolhido, só mostra a resposta 201 e nada além dela", async () => {
    const f = servir({ ...BASE, [POST]: [201, { ...CRIADO, motorista_nome: "Fulano de Tal" }] });
    render(<PaginaAutoatendimento />);
    await ateConferir();
    expect(screen.getByText("Passo 7 de 7")).toBeInTheDocument();
    expect(screen.getByText("***.***.***-25")).toBeInTheDocument();
    expect(screen.queryByText("52998224725")).not.toBeInTheDocument();
    expect(screen.queryByText("Agendamento feito")).not.toBeInTheDocument();
    await tocar("Confirmar agendamento");

    expect(await screen.findByRole("heading", { name: "Agendamento feito" })).toBeInTheDocument();
    expect(corpo(f)).toEqual({
      placa: "ABC1D23",
      cpf: "52998224725",
      tipo_operacao: "CARGA",
      produto_id: 30,
      data_prevista: HOJE,
      faixa_horario_id: 2,
    });
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("10:00 às 12:00")).toBeInTheDocument();
    expect(screen.queryByText("Fulano de Tal")).not.toBeInTheDocument();
  });
});

describe("CA-002: Descarga e leitor de código", () => {
  it("pede a nota, o Enter do leitor avança e o envio leva o código", async () => {
    const f = servir({ ...BASE, [POST]: [201, { ...CRIADO, tipo_operacao: "DESCARGA" }] });
    render(<PaginaAutoatendimento />);
    await tocar("Descarga");
    await tocar("Soja em grão");
    await tocar("Hoje");
    await tocar(/10:00 às 12:00/ as unknown as string);
    await digitar("Placa", "abc1d23");
    await tocar("Avançar");
    await digitar("CPF (só números)", "52998224725");
    await tocar("Avançar");
    expect(await screen.findByText("Passo 7 de 8")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Avançar" })).toBeDisabled();
    await digitar("Código da nota", "NF-9{Enter}");
    await screen.findByRole("heading", { name: "Confira os dados" });
    await tocar("Confirmar agendamento");
    await screen.findByRole("heading", { name: "Agendamento feito" });
    expect(corpo(f)).toMatchObject({ tipo_operacao: "DESCARGA", codigo_nota: "NF-9" });
  });
});

describe("CA-003: faixas", () => {
  it("desabilita faixa cheia, marca a sugerida e só avança com o toque", async () => {
    servir(BASE);
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    await tocar("Soja em grão");
    await tocar("Hoje");
    expect(await botao(/08:00 às 10:00 · sem vaga/ as unknown as string)).toBeDisabled();
    expect(await botao(/10:00 às 12:00 · 1 vaga · Sugerida/ as unknown as string)).toBeEnabled();
    expect(screen.getByRole("heading", { name: "Qual horário?" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Qual é a placa do caminhão?" }),
    ).not.toBeInTheDocument();
  });

  it("sem faixa com vaga avisa", async () => {
    servir({
      ...BASE,
      [URL_DISP]: [
        200,
        { data: HOJE, itens: [vaga(1, "08:00", "10:00", 0), vaga(2, "10:00", "12:00", 2, true)] },
      ],
    });
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    await tocar("Soja em grão");
    await tocar("Hoje");
    expect(await screen.findByText("Sem vaga neste dia. Escolha outro dia.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /encerrada/ })).toBeDisabled();
  });
});

describe("CA-004 a CA-006: recusas", () => {
  const falha = (
    status: number,
    codigo: string,
    campos: { campo: string; codigo: string }[] = [],
  ): Resposta => [status, erro(codigo, "Texto do backend que não deve aparecer.", campos)];

  it("DADOS_NAO_CONFEREM: uma só mensagem, volta à placa e mantém os dados", async () => {
    servir({ ...BASE, [POST]: falha(422, "DADOS_NAO_CONFEREM") });
    render(<PaginaAutoatendimento />);
    await ateConferir();
    await tocar("Confirmar agendamento");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Placa ou CPF não conferem. Confira os dois ou fale com o operador.",
    );
    expect(screen.getByLabelText("Placa")).toHaveValue("ABC1D23");
    expect(screen.queryByText(/backend/)).not.toBeInTheDocument();
  });

  it.each<[string, Resposta, string, string]>([
    [
      "placa inválida",
      falha(422, "CAMPO_INVALIDO", [{ campo: "placa", codigo: "PLACA_INVALIDA" }]),
      "Placa inválida. Confira as letras e os números.",
      "Qual é a placa do caminhão?",
    ],
    [
      "cpf inválido",
      falha(422, "CAMPO_INVALIDO", [{ campo: "cpf", codigo: "CAMPO_INVALIDO" }]),
      "CPF inválido. Confira os números.",
      "Qual é o seu CPF?",
    ],
    [
      "data passada",
      falha(422, "CAMPO_INVALIDO", [{ campo: "data_prevista", codigo: "DATA_NO_PASSADO" }]),
      "Essa data já passou. Escolha outra.",
      "Para qual dia?",
    ],
    [
      "faixa cheia",
      falha(409, "CONFLITO", [{ campo: "faixa_horario_id", codigo: "FAIXA_SEM_VAGA" }]),
      "Essa faixa não tem mais vaga. Escolha outra.",
      "Qual horário?",
    ],
  ])("%s mostra o texto fixo e volta ao passo", async (_n, resposta, texto, titulo) => {
    const f = servir({ ...BASE, [POST]: resposta });
    render(<PaginaAutoatendimento />);
    await ateConferir();
    await tocar("Confirmar agendamento");
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
    expect(screen.getByRole("heading", { name: titulo })).toBeInTheDocument();
    if (titulo === "Qual horário?") {
      await waitFor(() => {
        expect(
          f.mock.calls.filter(([u]) => typeof u === "string" && u.includes("disponibilidade")),
        ).toHaveLength(2);
      });
    }
  });

  it.each<[string, Resposta, string]>([
    [
      "veículo já agendado",
      falha(409, "CONFLITO", [{ campo: "veiculo_id", codigo: "VEICULO_JA_AGENDADO" }]),
      "Este veículo já tem um agendamento aberto. Fale com o operador.",
    ],
    [
      "bloqueio",
      falha(429, "AUTOATENDIMENTO_BLOQUEADO"),
      "Este totem está bloqueado por um tempo. Fale com o operador.",
    ],
    [
      "rede não permitida",
      falha(403, "REDE_NAO_PERMITIDA"),
      "O autoatendimento não está disponível aqui. Fale com o operador.",
    ],
    [
      "rota desligada",
      falha(404, "NAO_ENCONTRADO"),
      "O autoatendimento não está disponível aqui. Fale com o operador.",
    ],
    [
      "erro interno",
      falha(500, "ERRO_INTERNO"),
      "Não foi possível agendar agora. Nada foi salvo. Fale com o operador.",
    ],
    ["rede caída", "rede", "Não foi possível agendar agora. Nada foi salvo. Fale com o operador."],
  ])("%s não mostra sucesso", async (_n, resposta, texto) => {
    servir({ ...BASE, [POST]: resposta });
    render(<PaginaAutoatendimento />);
    await ateConferir();
    await tocar("Confirmar agendamento");
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
    expect(screen.queryByRole("heading", { name: "Agendamento feito" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar agendamento" })).toBeEnabled();
  });

  it("depois de 500, o motorista confirma de novo", async () => {
    let tentativas = 0;
    servir({
      ...BASE,
      [POST]: () => (++tentativas === 1 ? falha(500, "ERRO_INTERNO") : [201, CRIADO]),
    });
    render(<PaginaAutoatendimento />);
    await ateConferir();
    await tocar("Confirmar agendamento");
    await screen.findByRole("alert");
    await tocar("Confirmar agendamento");
    expect(await screen.findByRole("heading", { name: "Agendamento feito" })).toBeInTheDocument();
  });
});

describe("CA-008, CA-009: CPF e teclado", () => {
  it("CPF aceita só dígitos e só avança com 11", async () => {
    servir(BASE);
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    await tocar("Soja em grão");
    await tocar("Hoje");
    await tocar(/10:00 às 12:00/ as unknown as string);
    await digitar("Placa", "abc1d23");
    await tocar("Avançar");
    await digitar("CPF (só números)", "529.982-247abc2");
    expect(screen.getByLabelText("CPF (só números)")).toHaveValue("5299822472");
    expect(screen.getByRole("button", { name: "Avançar" })).toBeDisabled();
    await digitar("CPF (só números)", "599");
    expect(screen.getByLabelText("CPF (só números)")).toHaveValue("52998224725");
    expect(screen.getByRole("button", { name: "Avançar" })).toBeEnabled();
  });

  it("o teclado na tela escreve, apaga e convive com o teclado físico", async () => {
    servir(BASE);
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    await tocar("Soja em grão");
    await tocar("Hoje");
    await tocar(/10:00 às 12:00/ as unknown as string);
    const placa = await screen.findByLabelText("Placa");
    expect(placa).toHaveAttribute("inputmode", "none");
    for (const t of ["A", "B", "C", "1"]) await tocar(t);
    await userEvent.type(placa, "d");
    expect(placa).toHaveValue("ABC1D");
    await tocar("Apagar");
    expect(placa).toHaveValue("ABC1");
  });
});

describe("CA-010: inatividade", () => {
  it("60 segundos sem toque apagam os dados e voltam ao início", () => {
    vi.useFakeTimers();
    servir(BASE);
    render(<PaginaAutoatendimento />);
    fireEvent.click(screen.getByRole("button", { name: "Carga" }));
    expect(screen.getByText("Passo 2 de 7")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(59_000);
    });
    expect(screen.getByText("Passo 2 de 7")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(2_000);
    });
    expect(screen.getByRole("heading", { name: "O que você vai fazer?" })).toBeInTheDocument();
  });
});

describe("CA-011: falha ao carregar", () => {
  it("produtos: mostra o erro e tenta de novo", async () => {
    let falhou = true;
    servir({
      ...BASE,
      [URL_PRODUTOS]: () =>
        falhou
          ? [500, erro("ERRO_INTERNO", "x")]
          : [200, lista([{ id: 30, codigo: "S", descricao: "Soja em grão" }])],
    });
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível carregar. Tente de novo.",
    );
    falhou = false;
    await tocar("Tentar de novo");
    expect(await botao("Soja em grão")).toBeInTheDocument();
  });

  it("rota desligada diz que não está disponível", async () => {
    servir({ ...BASE, [URL_PRODUTOS]: [404, erro("NAO_ENCONTRADO", "x")] });
    render(<PaginaAutoatendimento />);
    await tocar("Carga");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "O autoatendimento não está disponível aqui.",
    );
  });
});
