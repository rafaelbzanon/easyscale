import { act, cleanup, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Agendamento } from "../../tipos/agendamentos";
import type { EstadoOperacao, LeituraPlaca } from "../../tipos/operacao";
import {
  abrir as abrirTela,
  chamadas,
  erro,
  lista,
  servir,
  sessao,
  type Resposta,
  type Rotas,
} from "../../utilitarios-testes";
import { canal, CanalFalso } from "../operacao/canal-falso";
import { depois, estadoOperacao, pesagem, T0 } from "../operacao/dados-teste";
import { hoje } from "../agendamentos/formatos";
import { PaginaDispositivos } from "./PaginaDispositivos";

const HOJE = hoje();
const OPERADOR = sessao("OPERADOR", ["CONSULTAR_OPERACAO", "TENTAR_NOVAMENTE"]);
const ADMIN = sessao("ADMINISTRADOR", [
  "CONSULTAR_OPERACAO",
  "TENTAR_NOVAMENTE",
  "INTERVIR_OPERACAO",
]);
const AUDITOR = sessao("AUDITOR", ["CONSULTAR_OPERACAO"]);

const leitura = (campos: Partial<LeituraPlaca> = {}): LeituraPlaca => ({
  id: 7,
  decisao: "NAO_AUTORIZADA",
  motivo: "CONFIANCA_BAIXA",
  placa_lida: "ABC1D23",
  placa_normalizada: "ABC1D23",
  confianca: "0.610",
  pesagem_id: null,
  agendamento_id: null,
  imagem_id: 5,
  capturada_em: T0,
  decidida_em: T0,
  ...campos,
});
const AGEND = {
  id: 31,
  placa: "ABC1D23",
  motorista_nome: "João Lima",
  faixa_hora_inicio: "08:00",
  faixa_hora_fim: "10:00",
  tipo_operacao: "CARGA",
} as Agendamento;
const URL_AGEND = `GET /api/agendamentos?pagina=1&status=AGENDADO&data_inicio=${HOJE}&data_fim=${HOJE}`;
const LIBERAR = "POST /api/leituras-placa/7/liberar-entrada";

async function abrir(estado: EstadoOperacao, rotas: Rotas = {}, quem = ADMIN) {
  const f = servir({
    "GET /api/operacao/estado": [200, estado],
    [URL_AGEND]: [200, lista([AGEND])],
    ...rotas,
  });
  abrirTela("/dispositivos", "dispositivos", <PaginaDispositivos />, quem);
  await screen.findByRole("heading", { name: "Dispositivos" });
  await vi.waitFor(() => canal());
  canal().abrir();
  await screen.findByText("Atualizada");
  return f;
}
const corpo = (f: ReturnType<typeof servir>) =>
  JSON.parse(chamadas(f, "POST")[0]?.[1]?.body as string) as Record<string, unknown>;

beforeEach(() => {
  CanalFalso.instancias = [];
  vi.stubGlobal("EventSource", CanalFalso);
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("CA-001: canal e tela desatualizada", () => {
  it("sincroniza e depois fica desatualizada sem mensagem, bloqueando as ações", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await abrir(estadoOperacao({ ultima_leitura_placa: leitura() }));
    await screen.findByLabelText("Agendamento de hoje (obrigatório)");
    expect(screen.getByRole("button", { name: "Liberar entrada" })).toBeDisabled(); // sem escolha ainda
    await act(async () => {
      await vi.advanceTimersByTimeAsync(16_000);
    });
    expect(screen.getByText("Tela desatualizada")).toBeInTheDocument();
    expect(screen.getByLabelText("Agendamento de hoje (obrigatório)")).toBeDisabled();
    expect(screen.getByLabelText("Motivo (obrigatório)")).toBeDisabled();
  });
});

describe("CA-002, CA-003: dispositivos", () => {
  it("mostra o modo de cada dispositivo; modo estranho é desconhecido", async () => {
    const base = estadoOperacao();
    const d = base.dispositivos;
    await abrir({
      ...base,
      dispositivos: {
        ...d,
        balanca: { ...d.balanca, modo: "REAL" },
        posicao: { ...d.posicao, modo: "OUTRO" as never },
      },
    });
    const secao = screen.getByRole("region", { name: "Dispositivos" });
    expect(within(secao).getByText("REAL")).toBeInTheDocument();
    expect(within(secao).getAllByText("SIMULADO")).toHaveLength(3);
    expect(within(secao).getByText("MODO DESCONHECIDO")).toBeInTheDocument();
  });

  it("falhas aparecem com palavra; cancela desconhecida não é aberta nem fechada", async () => {
    const base = estadoOperacao();
    const d = base.dispositivos;
    await abrir({
      ...base,
      dispositivos: {
        balanca: { ...d.balanca, comunicacao: "FALHA", motivo_falha: "SEM_RESPOSTA" },
        cancelas: [
          {
            ...d.cancelas[0],
            estado: "DESCONHECIDO",
            ultimo_comando: {
              comando: "ABRIR",
              resultado: "SEM_CONFIRMACAO",
              tentativas: 2,
              concluido_em: T0,
              pesagem_id: 12,
            },
          },
          d.cancelas[1],
        ],
        posicao: { ...d.posicao, resultado: "INCONCLUSIVA" },
        identificacao: { ...d.identificacao, resultado: "FALHA_LEITOR" },
      },
    });
    const secao = screen.getByRole("region", { name: "Dispositivos" });
    expect(within(secao).getByText("FALHA: sem resposta")).toBeInTheDocument();
    expect(within(secao).getByText("DESCONHECIDO")).toBeInTheDocument();
    expect(within(secao).getByText("Abrir: SEM CONFIRMAÇÃO (2 tentativas)")).toBeInTheDocument();
    expect(within(secao).getByText("Posição INCONCLUSIVA")).toBeInTheDocument();
    expect(within(secao).getByText("FALHA do leitor de placas")).toBeInTheDocument();
    const entrada = within(secao).getByText("Cancela de entrada").closest("li") as HTMLElement;
    expect(within(entrada).queryByText(/^(ABERTA|FECHADA)$/)).not.toBeInTheDocument();
  });
});

describe("CA-004: intervenção reaproveita as ações da fila", () => {
  it("conta as pesagens e envia a ação com versão e motivo", async () => {
    const parada = pesagem({
      situacao: "AGUARDANDO_INTERVENCAO",
      situacao_anterior: "POSICIONADA_INICIAL",
      motivo_intervencao: "TEMPO_ESGOTADO",
      acoes_disponiveis: ["TENTAR_NOVAMENTE"],
    });
    const f = await abrir(estadoOperacao({ pesagens_abertas: [parada] }), {
      "POST /api/pesagens/12/tentar-novamente": [
        200,
        { ...parada, versao: 4, situacao: "POSICIONADA_INICIAL" },
      ],
    });
    expect(screen.getByText("1 pesagem aguardando intervenção")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    await userEvent.type(screen.getByLabelText("Motivo"), "Balança conferida");
    await userEvent.click(screen.getByRole("button", { name: /Confirmar/ }));
    expect(
      await screen.findByText("Pedido aceito. O resultado chega pelos eventos."),
    ).toBeInTheDocument();
    expect(corpo(f)).toEqual({ versao: 3, motivo: "Balança conferida" });
  });
});

describe("CA-005, CA-006, CA-007: liberação de entrada", () => {
  const comLeitura = (l: LeituraPlaca | null) => estadoOperacao({ ultima_leitura_placa: l });

  it("administrador escolhe o agendamento, informa o motivo e só o 201 mostra o sucesso", async () => {
    const nova = pesagem({
      id: 50,
      placa: "XYZ9876",
      situacao: "AGUARDANDO_BALANCA_INICIAL",
      liberacao_manual: true,
      atualizado_em: depois(5),
    });
    const f = await abrir(comLeitura(leitura()), { [LIBERAR]: [201, nova] });
    const escolha = await screen.findByLabelText("Agendamento de hoje (obrigatório)");
    expect(escolha).toHaveValue(""); // nada pré-selecionado
    expect(screen.getByText(/Não autorizada: Leitura com confiança baixa/)).toBeInTheDocument();
    const botao = screen.getByRole("button", { name: "Liberar entrada" });
    expect(botao).toBeDisabled();
    await userEvent.selectOptions(escolha, "31");
    expect(botao).toBeDisabled(); // falta o motivo
    await userEvent.type(screen.getByLabelText("Motivo (obrigatório)"), "Placa conferida no pátio");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    await userEvent.click(botao);
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Entrada liberada para o agendamento.",
    );
    expect(corpo(f)).toEqual({ agendamento_id: 31, motivo: "Placa conferida no pátio" });
    expect(screen.getByText("XYZ9876")).toBeInTheDocument(); // a pesagem devolvida entra na fila
  });

  it("motivo que não pode ser liberado mostra o aviso e não o formulário", async () => {
    await abrir(comLeitura(leitura({ motivo: "SEM_AGENDAMENTO" })));
    expect(screen.getByText(/Esse motivo não pode ser liberado aqui/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Agendamento de hoje (obrigatório)")).not.toBeInTheDocument();
  });

  it("leitura autorizada, já liberada ou ausente não oferece liberação", async () => {
    await abrir(comLeitura(leitura({ decisao: "AUTORIZADA", motivo: null, pesagem_id: 3 })));
    expect(
      screen.getByText("A última leitura foi autorizada. Não há o que liberar."),
    ).toBeInTheDocument();
    cleanup();
    CanalFalso.instancias = [];
    await abrir(comLeitura(leitura({ pesagem_id: 9 })));
    expect(screen.getByText("Essa leitura já gerou a pesagem nº 9.")).toBeInTheDocument();
    cleanup();
    CanalFalso.instancias = [];
    await abrir(comLeitura(null));
    expect(screen.getByText("Nenhuma placa lida.")).toBeInTheDocument();
  });

  it("sem agendamento hoje avisa e não deixa enviar", async () => {
    await abrir(comLeitura(leitura()), { [URL_AGEND]: [200, lista([])] });
    expect(
      await screen.findByText("Nenhum agendamento para hoje. Crie o agendamento antes."),
    ).toBeInTheDocument();
  });

  it("falha ao listar os agendamentos mostra erro", async () => {
    await abrir(comLeitura(leitura()), {
      [URL_AGEND]: [500, erro("ERRO_INTERNO", "Erro interno.")],
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno.");
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
  });
});

describe("CA-008: recusas", () => {
  const conflito = (campo: string, codigo: string): Resposta => [
    409,
    erro("CONFLITO", "x", [{ campo, codigo }]),
  ];
  async function tentar(resposta: Resposta) {
    await abrir(estadoOperacao({ ultima_leitura_placa: leitura() }), { [LIBERAR]: resposta });
    await userEvent.selectOptions(
      await screen.findByLabelText("Agendamento de hoje (obrigatório)"),
      "31",
    );
    await userEvent.type(screen.getByLabelText("Motivo (obrigatório)"), "Conferido");
    await userEvent.click(screen.getByRole("button", { name: "Liberar entrada" }));
  }

  it.each<[string, Resposta, string]>([
    [
      "leitura velha",
      conflito("leitura_placa_id", "LEITURA_DESATUALIZADA"),
      "Chegou uma leitura mais nova. Confira a última placa lida.",
    ],
    [
      "leitura já liberada",
      conflito("leitura_placa_id", "LEITURA_NAO_LIBERAVEL"),
      "Essa leitura já foi liberada ou não precisa de liberação.",
    ],
    [
      "motivo",
      conflito("leitura_placa_id", "MOTIVO_NAO_SUBSTITUIVEL"),
      "Esse motivo não pode ser liberado aqui.",
    ],
    [
      "veículo inativo",
      conflito("agendamento_id", "VEICULO_INATIVO"),
      "O veículo do agendamento está inativo.",
    ],
    [
      "motorista inativo",
      conflito("agendamento_id", "MOTORISTA_INATIVO"),
      "O motorista do agendamento está inativo.",
    ],
    [
      "operação aberta",
      conflito("agendamento_id", "OPERACAO_JA_ABERTA"),
      "Esse veículo já tem uma operação aberta.",
    ],
    [
      "sem agendamento",
      conflito("agendamento_id", "SEM_AGENDAMENTO"),
      "O agendamento escolhido não vale para hoje.",
    ],
    ["403", [403, erro("SEM_PERMISSAO", "x")], "Você não tem permissão para esta ação."],
    ["rede", "rede", "Sem resposta válida do servidor."],
  ])("%s mostra o texto e mantém o formulário, sem sucesso", async (_n, resposta, texto) => {
    await tentar(resposta);
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Motivo (obrigatório)")).toHaveValue("Conferido");
  });
});

describe("CA-009: leitura mais nova", () => {
  it("reinicia o formulário", async () => {
    await abrir(estadoOperacao({ ultima_leitura_placa: leitura() }));
    await userEvent.type(await screen.findByLabelText("Motivo (obrigatório)"), "Conferido");
    canal().emitir(
      "leitura_placa",
      leitura({ id: 8, placa_normalizada: "QQQ0000", decidida_em: depois(30) }),
    );
    expect(await screen.findByText("QQQ0000")).toBeInTheDocument();
    expect(await screen.findByLabelText("Motivo (obrigatório)")).toHaveValue("");
  });
});

describe("CA-011: perfis", () => {
  it.each([
    ["OPERADOR", OPERADOR],
    ["AUDITOR", AUDITOR],
  ])("%s não vê a liberação de entrada", async (_n, quem) => {
    await abrir(estadoOperacao({ ultima_leitura_placa: leitura() }), {}, quem);
    expect(
      screen.queryByRole("region", { name: "Liberação manual de entrada" }),
    ).not.toBeInTheDocument();
  });

  it("auditor não vê botão de ação", async () => {
    const parada = pesagem({
      situacao: "AGUARDANDO_INTERVENCAO",
      acoes_disponiveis: ["TENTAR_NOVAMENTE", "CANCELAR"],
    });
    await abrir(estadoOperacao({ pesagens_abertas: [parada] }), {}, AUDITOR);
    expect(
      screen.queryByRole("button", { name: /Tentar novamente|Cancelar/ }),
    ).not.toBeInTheDocument();
  });
});
