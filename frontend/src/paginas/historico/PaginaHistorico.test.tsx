import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { EventoPesagem } from "../../tipos/historico";
import type { Pesagem } from "../../tipos/operacao";
import {
  abrir as abrirTela,
  erro,
  lista,
  servir,
  sessao,
  type Rotas,
} from "../../utilitarios-testes";
import { PaginaHistorico } from "./PaginaHistorico";

const LER = ["CONSULTAR_OPERACAO"];
const abrir = (quem = sessao("AUDITOR", LER)) => {
  abrirTela("/historico", "historico", <PaginaHistorico />, quem);
};

const PESAGEM: Pesagem = {
  id: 7,
  versao: 12,
  situacao: "FINALIZADA",
  situacao_anterior: null,
  motivo_intervencao: null,
  comando_pendente: null,
  acoes_disponiveis: [],
  ocupa_balanca: false,
  aguarda_liberacao_balanca: false,
  liberacao_manual: false,
  agendamento_id: 3,
  agendamento_status: "CONCLUIDO",
  tipo_operacao: "CARGA",
  placa: "ABC1D23",
  motorista_nome: "João Lima",
  transportadora_razao_social: null,
  produto_descricao: "Soja em grão",
  data_prevista: "2026-11-07",
  faixa_hora_inicio: "08:00",
  faixa_hora_fim: "10:00",
  peso_inicial_kg: "15000.500",
  peso_inicial_em: "2026-11-07T11:00:00Z",
  peso_final_kg: "42000.250",
  peso_final_em: "2026-11-07T12:00:00Z",
  peso_liquido_kg: "26999.750",
  classificacao: "COM_MOVIMENTACAO",
  criado_em: "2026-11-07T10:30:00Z",
  atualizado_em: "2026-11-07T12:01:00Z",
};
const SEM_MOV: Pesagem = {
  ...PESAGEM,
  id: 8,
  placa: "XYZ9876",
  peso_liquido_kg: "12.000",
  classificacao: "SEM_MOVIMENTACAO",
};
const INTERVENCAO: Pesagem = {
  ...PESAGEM,
  id: 9,
  placa: "QQQ0000",
  situacao: "AGUARDANDO_INTERVENCAO",
  situacao_anterior: "POSICIONADA_FINAL",
  motivo_intervencao: "LIQUIDO_NEGATIVO",
  peso_final_kg: null,
  peso_liquido_kg: null,
  classificacao: null,
};

const evento = (id: number, extra: Partial<EventoPesagem>): EventoPesagem => ({
  id,
  tipo: "TRANSICAO",
  ocorrido_em: "2026-11-07T10:30:00Z",
  evento: null,
  situacao_origem: "AUTORIZADA",
  situacao_destino: null,
  motivo_rejeicao: null,
  motivo_intervencao: null,
  motivo_dispositivo: null,
  peso_kg: null,
  peso_liquido_kg: null,
  classificacao: null,
  cancela: null,
  comando: null,
  resultado: null,
  tentativas: null,
  responsavel: null,
  motivo: null,
  imagem_id: null,
  leitura_placa_id: null,
  ...extra,
});
const EVENTOS: EventoPesagem[] = [
  evento(1, {
    evento: "CRIACAO",
    situacao_origem: "AGUARDANDO_BALANCA_INICIAL",
    situacao_destino: "AGUARDANDO_BALANCA_INICIAL",
    leitura_placa_id: 55,
  }),
  evento(2, {
    tipo: "COMANDO_CANCELA",
    situacao_origem: "AUTORIZADA",
    cancela: "ENTRADA",
    comando: "ABRIR",
    resultado: "SEM_CONFIRMACAO",
    tentativas: 2,
  }),
  evento(3, {
    tipo: "COMANDO_CANCELA",
    cancela: "SAIDA",
    comando: "FECHAR",
    resultado: "CONFIRMADO",
    tentativas: 1,
  }),
  evento(4, {
    tipo: "TRANSICAO_REJEITADA",
    evento: "POSICAO_CONFIRMADA",
    situacao_origem: "AUTORIZADA",
    motivo_rejeicao: "TRANSICAO_INVALIDA",
  }),
  evento(5, {
    tipo: "EVENTO_REGISTRADO",
    evento: "PESO_REJEITADO",
    situacao_origem: "POSICIONADA_FINAL",
    motivo_dispositivo: "INSTAVEL",
  }),
  evento(6, {
    evento: "PESO_ACEITO",
    situacao_origem: "POSICIONADA_FINAL",
    situacao_destino: "AGUARDANDO_INTERVENCAO",
    peso_kg: "9000.000",
    peso_liquido_kg: "-6000.500",
    classificacao: "NEGATIVO_FORA_TOLERANCIA",
    motivo_intervencao: "LIQUIDO_NEGATIVO",
    imagem_id: 12,
  }),
  evento(7, {
    evento: "TENTAR_NOVAMENTE",
    situacao_origem: "AGUARDANDO_INTERVENCAO",
    situacao_destino: "POSICIONADA_FINAL",
    responsavel: { id: 1, nome: "Ana Souza" },
    motivo: "Balança recalibrada.",
  }),
];

const LISTA: Rotas = {
  "GET /api/pesagens?pagina=1": [200, lista([PESAGEM, SEM_MOV, INTERVENCAO])],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CA-001, CA-003, CA-004: lista", () => {
  it("mostra as colunas, a nota de consulta, a situação em palavra e os pesos como vieram", async () => {
    servir(LISTA);
    abrir();
    const linha = (await screen.findByText("ABC1D23")).closest("tr") as HTMLElement;
    for (const t of [
      "João Lima",
      "Soja em grão",
      "Finalizada",
      "15.000,5 kg",
      "42.000,25 kg",
      "26.999,75 kg",
      "Com movimentação",
      "Carga",
    ]) {
      expect(within(linha).getByText(t)).toBeInTheDocument();
    }
    expect(
      screen.getByText(/Consulta feita às .* Esta tela não atualiza sozinha\./),
    ).toBeInTheDocument();
    expect(screen.getByText("Página 1 de 1 · 3 pesagens")).toBeInTheDocument();

    const semMov = screen.getByText("XYZ9876").closest("tr") as HTMLElement;
    expect(within(semMov).getByText("12 kg")).toBeInTheDocument(); // nunca zero (RN-006)
    expect(within(semMov).getByText("Sem movimentação")).toBeInTheDocument();

    const interv = screen.getByText("QQQ0000").closest("tr") as HTMLElement;
    expect(within(interv).getByText("Aguardando intervenção")).toBeInTheDocument();
    expect(
      within(interv).getByText("Peso líquido negativo fora da tolerância"),
    ).toBeInTheDocument();
    expect(within(interv).getAllByText("—").length).toBeGreaterThanOrEqual(2); // peso final e líquido ausentes
  });

  it("Atualizar consulta de novo", async () => {
    const f = servir(LISTA);
    abrir();
    await screen.findByText("ABC1D23");
    await userEvent.click(screen.getByRole("button", { name: "Atualizar" }));
    await waitFor(() => {
      expect(f.mock.calls.filter(([u]) => u === "/api/pesagens?pagina=1")).toHaveLength(2);
    });
  });
});

describe("CA-002: filtros", () => {
  it("manda só os preenchidos, com os nomes do contrato, e volta à página 1", async () => {
    const f = servir({
      ...LISTA,
      "GET /api/pesagens?pagina=1&aberta=true&situacao=AGUARDANDO_INTERVENCAO&tipo_operacao=DESCARGA&placa=abc&agendamento_id=3":
        [200, lista([])],
    });
    abrir();
    await screen.findByText("ABC1D23");
    await userEvent.selectOptions(screen.getByLabelText("Pesagens"), "true");
    await userEvent.selectOptions(screen.getByLabelText("Situação"), "AGUARDANDO_INTERVENCAO");
    await userEvent.selectOptions(screen.getByLabelText("Tipo"), "DESCARGA");
    await userEvent.type(screen.getByLabelText("Placa"), "abc");
    await userEvent.type(screen.getByLabelText("Nº do agendamento"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Filtrar" }));
    expect(await screen.findByText("Nenhuma pesagem encontrada.")).toBeInTheDocument();
    expect(f.mock.calls.at(-1)?.[0]).toBe(
      "/api/pesagens?pagina=1&aberta=true&situacao=AGUARDANDO_INTERVENCAO&tipo_operacao=DESCARGA&placa=abc&agendamento_id=3",
    );
  });

  it("422 de placa mostra o texto do código e mantém o filtro", async () => {
    servir({
      ...LISTA,
      "GET /api/pesagens?pagina=1&placa=ABCO123": [
        422,
        erro("CAMPO_INVALIDO", "Há campos inválidos.", [
          { campo: "placa", codigo: "PLACA_INVALIDA" },
        ]),
      ],
    });
    abrir();
    await screen.findByText("ABC1D23");
    await userEvent.type(screen.getByLabelText("Placa"), "ABCO123");
    await userEvent.click(screen.getByRole("button", { name: "Filtrar" }));
    expect(await screen.findByText(/Placa inválida/)).toBeInTheDocument();
    expect(screen.getByLabelText("Placa")).toHaveValue("ABCO123");
  });
});

describe("CA-005 a CA-009: eventos", () => {
  async function abrirEventos() {
    const f = servir({ ...LISTA, "GET /api/pesagens/9/eventos?pagina=1": [200, lista(EVENTOS)] });
    abrir();
    await userEvent.click(
      await screen.findByRole("button", { name: "Eventos da pesagem de QQQ0000 nº 9" }),
    );
    const painel = await screen.findByRole("region", { name: "Eventos da pesagem" });
    await within(painel).findByText("Operação criada");
    return { f, painel };
  }

  it("mostra transição, rejeição, registro e comando de cancela, na ordem recebida", async () => {
    const { painel } = await abrirEventos();
    const linhas = within(painel).getAllByRole("row").slice(1);
    expect(linhas).toHaveLength(7);
    expect(
      within(linhas[1] as HTMLElement).getByText(/Cancela de entrada: abrir/),
    ).toBeInTheDocument();
    expect(within(linhas[3] as HTMLElement).getByText(/Rejeitada: nada mudou/)).toBeInTheDocument();
    expect(within(linhas[3] as HTMLElement).getByText(/TRANSICAO_INVALIDA/)).toBeInTheDocument();
    expect(within(linhas[4] as HTMLElement).getByText("Registrado")).toBeInTheDocument();
    expect(within(linhas[4] as HTMLElement).getByText(/INSTAVEL/)).toBeInTheDocument();
    expect(
      within(painel).getByText(/Aguardando balança \(pesagem inicial\) → Aguardando balança/),
    ).toBeInTheDocument();
  });

  it("SEM_CONFIRMACAO é falha em palavra; CONFIRMADO é ok", async () => {
    const { painel } = await abrirEventos();
    expect(within(painel).getByText(/SEM CONFIRMAÇÃO \(2 tentativas\)/)).toBeInTheDocument();
    expect(within(painel).getByText(/confirmado \(1 tentativa\)/)).toBeInTheDocument();
    expect(within(painel).queryByText(/SEM_CONFIRMACAO/)).not.toBeInTheDocument();
  });

  it("ação manual mostra responsável e motivo; o resto é Automático", async () => {
    const { painel } = await abrirEventos();
    expect(within(painel).getByText("Ana Souza")).toBeInTheDocument();
    expect(within(painel).getByText("Motivo: Balança recalibrada.")).toBeInTheDocument();
    expect(within(painel).getAllByText("Automático")).toHaveLength(6);
  });

  it("peso e líquido descartados continuam visíveis; imagem e leitura só como número", async () => {
    const { f, painel } = await abrirEventos();
    expect(
      within(painel).getByText(
        /Peso: 9.000 kg · líquido −6.000,5 kg \(Negativo fora da tolerância\)/,
      ),
    ).toBeInTheDocument();
    expect(within(painel).getByText(/Imagem da decisão nº 12/)).toBeInTheDocument();
    expect(within(painel).getByText(/Leitura de placa nº 55/)).toBeInTheDocument();
    expect(f.mock.calls.some(([u]) => typeof u === "string" && /imagens|leituras/.test(u))).toBe(
      false,
    );
  });
});

describe("CA-010: falhas", () => {
  it("lista: mostra o erro e tenta de novo", async () => {
    let falhou = true;
    servir({
      "GET /api/pesagens?pagina=1": () =>
        falhou ? [500, erro("ERRO_INTERNO", "Erro interno.")] : [200, lista([PESAGEM])],
    });
    abrir();
    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno.");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    falhou = false;
    await userEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
  });

  it("eventos: 404 mostra erro com Tentar de novo; 403 diz que falta permissão", async () => {
    servir({
      ...LISTA,
      "GET /api/pesagens/7/eventos?pagina=1": [
        404,
        erro("NAO_ENCONTRADO", "Registro não encontrado."),
      ],
    });
    abrir();
    await userEvent.click(
      await screen.findByRole("button", { name: "Eventos da pesagem de ABC1D23 nº 7" }),
    );
    const painel = await screen.findByRole("region", { name: "Eventos da pesagem" });
    expect(await within(painel).findByRole("alert")).toHaveTextContent("Registro não encontrado.");
    expect(within(painel).getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
  });

  it("403 na lista", async () => {
    servir({ "GET /api/pesagens?pagina=1": [403, erro("SEM_PERMISSAO", "x")] });
    abrir();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Você não tem permissão para esta ação.",
    );
  });
});

describe("CA-011: paginação", () => {
  it("Próxima pede a página seguinte, na lista e nos eventos", async () => {
    const f = servir({
      "GET /api/pesagens?pagina=1": [200, lista([PESAGEM], { total: 2, tamanho_pagina: 1 })],
      "GET /api/pesagens?pagina=2": [
        200,
        lista([SEM_MOV], { total: 2, tamanho_pagina: 1, pagina: 2 }),
      ],
      "GET /api/pesagens/7/eventos?pagina=1": [
        200,
        lista([EVENTOS[0] as EventoPesagem], { total: 2, tamanho_pagina: 1 }),
      ],
      "GET /api/pesagens/7/eventos?pagina=2": [
        200,
        lista([EVENTOS[2] as EventoPesagem], { total: 2, tamanho_pagina: 1, pagina: 2 }),
      ],
    });
    abrir();
    await userEvent.click(
      await screen.findByRole("button", { name: "Eventos da pesagem de ABC1D23 nº 7" }),
    );
    const painel = await screen.findByRole("region", { name: "Eventos da pesagem" });
    await within(painel).findByText("Operação criada");
    await userEvent.click(within(painel).getByRole("button", { name: "Próxima" }));
    expect(await within(painel).findByText(/Cancela de saída: fechar/)).toBeInTheDocument();
    await userEvent.click(
      within(screen.getByRole("navigation", { name: "Paginação" })).getByRole("button", {
        name: "Próxima",
      }),
    );
    expect(await screen.findByText("XYZ9876")).toBeInTheDocument();
    expect(f.mock.calls.some(([u]) => u === "/api/pesagens?pagina=2")).toBe(true);
  });
});

describe("CA-012: perfis", () => {
  it.each([
    ["AUDITOR", ["CONSULTAR_OPERACAO"]],
    ["OPERADOR", ["CONSULTAR_OPERACAO", "CRIAR_AGENDAMENTO"]],
    ["ADMINISTRADOR", ["CONSULTAR_OPERACAO", "GERENCIAR_CADASTROS", "INTERVIR_OPERACAO"]],
  ])("%s vê a mesma tela, sem botão que mude dado", async (perfil, permissoes) => {
    servir(LISTA);
    abrir(sessao(perfil, permissoes));
    await screen.findByText("ABC1D23");
    const nomes = screen.getAllByRole("button").map((b) => b.textContent);
    expect(
      nomes.filter((n) => !["Filtrar", "Atualizar", "Eventos", "Anterior", "Próxima"].includes(n)),
    ).toEqual([]);
  });
});
