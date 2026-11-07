import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Agendamento, Disponibilidade, FaixaHorario } from "../../tipos/agendamentos";
import type { Motorista, Produto, Transportadora, Veiculo } from "../../tipos/cadastros";
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
import { hoje } from "./formatos";
import { PaginaAgendamentos } from "./PaginaAgendamentos";

const HOJE = hoje();
const CONSULTA = ["CONSULTAR_AGENDAMENTOS"];
const AUDITOR = sessao("AUDITOR", CONSULTA);
const OPERADOR = sessao("OPERADOR", [...CONSULTA, "CRIAR_AGENDAMENTO", "CONSULTAR_CADASTROS"]);
const ADMIN = sessao("ADMINISTRADOR", [
  ...CONSULTA,
  "CRIAR_AGENDAMENTO",
  "GERENCIAR_AGENDAMENTOS",
  "CONSULTAR_CADASTROS",
  "GERENCIAR_CADASTROS",
]);

const abrir = (rota: string, quem = ADMIN) => {
  abrirTela(rota, "agendamentos", <PaginaAgendamentos />, quem);
};

const AGEND: Agendamento = {
  id: 1,
  veiculo_id: 10,
  motorista_id: 20,
  transportadora_id: 5,
  produto_id: 30,
  tipo_operacao: "CARGA",
  data_prevista: HOJE,
  faixa_horario_id: 2,
  codigo_nota: null,
  observacao: null,
  status: "AGENDADO",
  origem: "USUARIO",
  criado_por: 1,
  criado_em: "2026-11-07T12:00:00Z",
  cancelado_por: null,
  cancelado_em: null,
  motivo_cancelamento: null,
  placa: "ABC1D23",
  motorista_nome: "João Lima",
  transportadora_razao_social: "Rota Sul Ltda",
  produto_descricao: "Soja em grão",
  faixa_hora_inicio: "10:00",
  faixa_hora_fim: "12:00",
};
const CANCELADO: Agendamento = { ...AGEND, id: 2, status: "CANCELADO", placa: "XYZ9876" };

const VEICULO = (
  id: number,
  placa: string,
  transp: number | null,
  mot: number | null,
): Veiculo => ({
  id,
  ativo: true,
  placa,
  formato_placa: "MERCOSUL",
  tipo_veiculo_id: 1,
  transportadora_id: transp,
  motorista_padrao_id: mot,
  marca: null,
  modelo: null,
  eixos: null,
  tara_kg: null,
  capacidade_kg: null,
});
const MOTORISTA: Motorista = {
  id: 20,
  ativo: true,
  nome: "João Lima",
  cpf: null,
  cpf_mascarado: "***.982.247-**",
  transportadora_id: null,
  cnh_numero: null,
  cnh_categoria: null,
  data_validade_cnh: null,
  telefone: null,
};
const TRANSP: Transportadora = {
  id: 5,
  ativo: true,
  razao_social: "Rota Sul Ltda",
  nome_fantasia: null,
  cnpj: "11222333000181",
  telefone: null,
  email: null,
};
const PRODUTO: Produto = {
  id: 30,
  ativo: true,
  codigo: "SOJA",
  descricao: "Soja em grão",
  unidade: "KG",
};
const FAIXA: FaixaHorario = {
  id: 1,
  hora_inicio: "08:00",
  hora_fim: "10:00",
  capacidade: 2,
  ativo: true,
};

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
const URL_DISP = `GET /api/faixas-horario/disponibilidade?data=${HOJE}`;
const URL_LISTA = `GET /api/agendamentos?pagina=1&data_inicio=${HOJE}`;

const APOIO: Rotas = {
  "GET /api/veiculos?pagina=1": [
    200,
    lista([VEICULO(10, "ABC1D23", 5, 20), VEICULO(11, "XYZ9876", null, null)]),
  ],
  "GET /api/motoristas?pagina=1": [200, lista([MOTORISTA])],
  "GET /api/transportadoras?pagina=1": [200, lista([TRANSP])],
  "GET /api/produtos?pagina=1": [200, lista([PRODUTO])],
  [URL_DISP]: [200, DISP],
};
const BASE: Rotas = { ...APOIO, [URL_LISTA]: [200, lista([AGEND, CANCELADO])] };

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CA-001: lista", () => {
  it("mostra o resumo, o status em palavra e filtra", async () => {
    const f = servir(BASE);
    abrir("/agendamentos");
    const linha = (await screen.findByText("ABC1D23")).closest("tr") as HTMLElement;
    for (const t of [
      "João Lima",
      "Rota Sul Ltda",
      "Soja em grão",
      "10:00–12:00",
      "Carga",
      "Agendado",
      "Usuário",
    ]) {
      expect(within(linha).getByText(t)).toBeInTheDocument();
    }
    expect(within(screen.getByRole("table")).getByText("Cancelado")).toBeInTheDocument();
    expect(f.mock.calls[0]?.[0]).toBe(`/api/agendamentos?pagina=1&data_inicio=${HOJE}`);

    await userEvent.selectOptions(screen.getByLabelText("Status"), "CANCELADO");
    await userEvent.type(screen.getByLabelText("Placa"), "xyz");
    await userEvent.click(screen.getByRole("button", { name: "Filtrar" }));
    await waitFor(() => {
      expect(
        f.mock.calls.some(
          ([u]) =>
            u === `/api/agendamentos?pagina=1&data_inicio=${HOJE}&status=CANCELADO&placa=xyz`,
        ),
      ).toBe(true);
    });
  });
});

describe("CA-002: perfis", () => {
  it("auditor só consulta e não vê as faixas", async () => {
    servir(BASE);
    abrir("/agendamentos", AUDITOR);
    await screen.findByText("ABC1D23");
    expect(screen.queryByRole("button", { name: /Novo|Editar|Cancelar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Faixas de horário" })).not.toBeInTheDocument();
  });

  it("operador cria, mas não edita nem cancela", async () => {
    servir(BASE);
    abrir("/agendamentos", OPERADOR);
    await screen.findByText("ABC1D23");
    expect(screen.getByRole("button", { name: "Novo agendamento" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar|Cancelar/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Faixas de horário" })).toBeInTheDocument();
  });

  it("administrador edita e cancela só o que está Agendado", async () => {
    servir(BASE);
    abrir("/agendamentos");
    await screen.findByText("ABC1D23");
    expect(screen.getAllByRole("button", { name: /^Editar/ })).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: "Editar agendamento de ABC1D23" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Cancelar agendamento/ })).toHaveLength(1);
  });
});

async function abrirNovo(rotas: Rotas = BASE, quem = ADMIN) {
  const f = servir(rotas);
  abrir("/agendamentos", quem);
  await userEvent.click(await screen.findByRole("button", { name: "Novo agendamento" }));
  await screen.findByRole("heading", { name: "Novo agendamento" });
  return f;
}
const esperarSugestao = () =>
  waitFor(() => {
    expect(screen.getByLabelText("Faixa de horário (obrigatório)")).toHaveValue("2");
  });
const preencher = async () => {
  await userEvent.selectOptions(await screen.findByLabelText("Veículo (obrigatório)"), "ABC1D23");
  await userEvent.selectOptions(screen.getByLabelText("Produto (obrigatório)"), "Soja em grão");
  await userEvent.selectOptions(screen.getByLabelText("Tipo de operação (obrigatório)"), "Carga");
};
const corpo = (f: ReturnType<typeof servir>, metodo = "POST") =>
  JSON.parse(chamadas(f, metodo)[0]?.[1]?.body as string) as Record<string, unknown>;

describe("CA-003 a CA-006: criar", () => {
  it("sugere a primeira faixa com vaga, pré-preenche pelo veículo e envia a faixa escolhida", async () => {
    const f = await abrirNovo({
      ...BASE,
      "POST /api/agendamentos": [201, AGEND],
    });
    const faixa = await screen.findByLabelText("Faixa de horário (obrigatório)");
    await waitFor(() => {
      expect(faixa).toHaveValue("2");
    });
    expect(screen.getByText(/Sugerida: primeira faixa com vaga/)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /08:00–10:00 · 0 vagas · sem vaga/ })).toBeDisabled();

    await preencher();
    expect(screen.getByLabelText("Transportadora")).toHaveValue("5");
    expect(screen.getByLabelText("Motorista (obrigatório)")).toHaveValue("20");
    expect(screen.queryByText("Agendamento criado", { exact: false })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Criar agendamento" }));

    expect(await screen.findByText("Agendamento criado: faixa 10:00–12:00.")).toBeInTheDocument();
    expect(corpo(f)).toEqual({
      veiculo_id: 10,
      motorista_id: 20,
      transportadora_id: 5,
      produto_id: 30,
      tipo_operacao: "CARGA",
      data_prevista: HOJE,
      faixa_horario_id: 2,
    });
  });

  it("quem agenda troca a faixa sugerida", async () => {
    const f = await abrirNovo({ ...BASE, "POST /api/agendamentos": [201, AGEND] });
    await preencher();
    await userEvent.selectOptions(
      await screen.findByLabelText("Faixa de horário (obrigatório)"),
      "3",
    );
    expect(screen.queryByText(/Sugerida/)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Criar agendamento" }));
    await screen.findByText(/Agendamento criado/);
    expect(corpo(f).faixa_horario_id).toBe(3);
  });

  it("sem faixa com vaga avisa e não deixa enviar", async () => {
    await abrirNovo({
      ...BASE,
      [URL_DISP]: [
        200,
        { data: HOJE, itens: [vaga(1, "08:00", "10:00", 0), vaga(2, "10:00", "12:00", 2, true)] },
      ],
    });
    expect(await screen.findByText("Sem vaga neste dia.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Criar agendamento" })).toBeDisabled();
  });
});

describe("CA-007: código da nota", () => {
  it("só em Descarga; em Carga não é enviado", async () => {
    const f = await abrirNovo({ ...BASE, "POST /api/agendamentos": [201, AGEND] });
    await preencher();
    expect(screen.queryByLabelText("Código da nota")).not.toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText("Tipo de operação (obrigatório)"),
      "Descarga",
    );
    await userEvent.type(screen.getByLabelText("Código da nota"), "NF-123");
    await userEvent.selectOptions(screen.getByLabelText("Tipo de operação (obrigatório)"), "Carga");
    expect(screen.queryByLabelText("Código da nota")).not.toBeInTheDocument();
    await esperarSugestao();
    await userEvent.click(screen.getByRole("button", { name: "Criar agendamento" }));
    await screen.findByText(/Agendamento criado/);
    expect(corpo(f)).not.toHaveProperty("codigo_nota");
  });
});

describe("CA-008, CA-009: recusa no envio", () => {
  async function tentar(resposta: Resposta, rotas: Rotas = {}) {
    const f = await abrirNovo({ ...BASE, ...rotas, "POST /api/agendamentos": resposta });
    await preencher();
    await esperarSugestao();
    await userEvent.click(screen.getByRole("button", { name: "Criar agendamento" }));
    return f;
  }

  it.each<[string, Resposta, string]>([
    [
      "VEICULO_JA_AGENDADO",
      [
        409,
        erro("CONFLITO", "Conflito.", [{ campo: "veiculo_id", codigo: "VEICULO_JA_AGENDADO" }]),
      ],
      "Este veículo já tem um agendamento aberto.",
    ],
    [
      "DATA_NO_PASSADO",
      [
        422,
        erro("CAMPO_INVALIDO", "Inválido.", [
          { campo: "data_prevista", codigo: "DATA_NO_PASSADO" },
        ]),
      ],
      "A data já passou.",
    ],
  ])("%s mantém o formulário e mostra o texto do código", async (_n, resposta, texto) => {
    await tentar(resposta);
    expect(await screen.findByText(texto)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Novo agendamento" })).toBeInTheDocument();
    expect(screen.getByLabelText("Veículo (obrigatório)")).toHaveValue("10");
    expect(screen.queryByText(/Agendamento criado/)).not.toBeInTheDocument();
  });

  it("FAIXA_SEM_VAGA consulta a disponibilidade de novo", async () => {
    const f = await tentar([
      409,
      erro("CONFLITO", "Conflito.", [{ campo: "faixa_horario_id", codigo: "FAIXA_SEM_VAGA" }]),
    ]);
    expect(await screen.findByText("A faixa não tem mais vaga.")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        f.mock.calls.filter(([u]) => u === `/api/faixas-horario/disponibilidade?data=${HOJE}`),
      ).toHaveLength(2);
    });
  });

  it.each<[string, Resposta, string]>([
    ["403", [403, erro("SEM_PERMISSAO", "x")], "Você não tem permissão para esta ação."],
    ["500", [500, erro("ERRO_INTERNO", "Erro interno.")], "Erro interno."],
    ["rede caída", "rede", "Sem resposta válida do servidor."],
  ])("%s mostra erro e não fecha o formulário", async (_n, resposta, texto) => {
    await tentar(resposta);
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
    expect(screen.getByRole("heading", { name: "Novo agendamento" })).toBeInTheDocument();
    expect(screen.queryByText(/Agendamento criado/)).not.toBeInTheDocument();
  });

  it("falha na disponibilidade mostra erro e bloqueia o envio", async () => {
    await abrirNovo({ ...BASE, [URL_DISP]: [500, erro("ERRO_INTERNO", "Erro interno.")] });
    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno.");
    expect(screen.getByRole("button", { name: "Criar agendamento" })).toBeDisabled();
  });
});

describe("CA-010: editar", () => {
  const rotas: Rotas = { ...BASE, "GET /api/agendamentos/1": [200, AGEND] };

  it("sem alteração não envia; com alteração envia só o campo", async () => {
    const f = servir({
      ...rotas,
      "PATCH /api/agendamentos/1": [200, { ...AGEND, observacao: "Chega cedo" }],
    });
    abrir("/agendamentos");
    await userEvent.click(
      await screen.findByRole("button", { name: "Editar agendamento de ABC1D23" }),
    );
    await screen.findByRole("heading", { name: "Editar agendamento" });
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Salvar" })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    expect(chamadas(f, "PATCH")).toHaveLength(0);

    await userEvent.click(screen.getByRole("button", { name: "Editar agendamento de ABC1D23" }));
    await userEvent.type(await screen.findByLabelText("Observação"), "Chega cedo");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Salvar" })).toBeEnabled();
    });
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await screen.findByText("Salvo.");
    expect(corpo(f, "PATCH")).toEqual({ observacao: "Chega cedo" });
  });
});

describe("CA-011: cancelar", () => {
  it("exige motivo, mostra o efeito e envia o cancelamento", async () => {
    const f = servir({
      ...BASE,
      "POST /api/agendamentos/1/cancelar": [200, { ...AGEND, status: "CANCELADO" }],
    });
    abrir("/agendamentos");
    await userEvent.click(
      await screen.findByRole("button", { name: "Cancelar agendamento de ABC1D23" }),
    );
    expect(screen.getByText(/A vaga da faixa é liberada/)).toBeInTheDocument();
    const confirmar = screen.getByRole("button", { name: "Confirmar cancelamento" });
    expect(confirmar).toBeDisabled();
    await userEvent.type(screen.getByLabelText("Motivo (obrigatório)"), "Motorista desistiu.");
    await userEvent.click(confirmar);
    expect(await screen.findByText("Agendamento cancelado.")).toBeInTheDocument();
    expect(corpo(f)).toEqual({ motivo: "Motorista desistiu." });
  });

  it("409 mantém o painel e recarrega a lista", async () => {
    const f = servir({
      ...BASE,
      "POST /api/agendamentos/1/cancelar": [
        409,
        erro("CONFLITO", "Conflito.", [{ campo: "status", codigo: "STATUS_NAO_PERMITE" }]),
      ],
    });
    abrir("/agendamentos");
    await userEvent.click(
      await screen.findByRole("button", { name: "Cancelar agendamento de ABC1D23" }),
    );
    await userEvent.type(screen.getByLabelText("Motivo (obrigatório)"), "Erro de data.");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar cancelamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Conflito.");
    expect(screen.getByRole("heading", { name: "Cancelar agendamento" })).toBeInTheDocument();
    await waitFor(() => {
      expect(
        f.mock.calls.filter(([u]) => u === `/api/agendamentos?pagina=1&data_inicio=${HOJE}`),
      ).toHaveLength(2);
    });
  });
});

describe("CA-012: faixas", () => {
  const FAIXAS: Rotas = { "GET /api/faixas-horario?ativo=true&pagina=1": [200, lista([FAIXA])] };

  it("operador só consulta", async () => {
    servir(FAIXAS);
    abrir("/agendamentos?visao=faixas", OPERADOR);
    expect(await screen.findByText("08:00")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Nova faixa|Editar/ })).not.toBeInTheDocument();
  });

  it("administrador cria uma faixa", async () => {
    const f = servir({ ...FAIXAS, "POST /api/faixas-horario": [201, FAIXA] });
    abrir("/agendamentos?visao=faixas");
    await userEvent.click(await screen.findByRole("button", { name: "Nova faixa" }));
    fireEvent.change(screen.getByLabelText("Início (obrigatório)"), { target: { value: "08:00" } });
    fireEvent.change(screen.getByLabelText("Fim (obrigatório)"), { target: { value: "10:00" } });
    await userEvent.type(screen.getByLabelText("Capacidade (vagas por dia) (obrigatório)"), "3");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await screen.findByText("Salvo.");
    expect(corpo(f)).toEqual({ hora_inicio: "08:00", hora_fim: "10:00", capacidade: 3 });
  });

  it("desativar avisa o efeito; mudar horário com agendamentos mostra o texto do código", async () => {
    const f = servir({
      ...FAIXAS,
      "GET /api/faixas-horario/1": [200, FAIXA],
      "PATCH /api/faixas-horario/1": [
        409,
        erro("CONFLITO", "Conflito.", [{ campo: "hora_inicio", codigo: "FAIXA_COM_AGENDAMENTOS" }]),
      ],
    });
    abrir("/agendamentos?visao=faixas");
    await userEvent.click(await screen.findByRole("button", { name: "Editar 08:00" }));
    await userEvent.click(await screen.findByLabelText("Cadastro ativo"));
    expect(screen.getByText(/Faixa inativa não recebe agendamentos novos/)).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText("Cadastro ativo"));
    fireEvent.change(screen.getByLabelText("Início (obrigatório)"), { target: { value: "08:30" } });
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    expect(
      await screen.findByText("Há agendamentos nesta faixa. Desative-a e crie outra."),
    ).toBeInTheDocument();
    expect(corpo(f, "PATCH")).toEqual({ hora_inicio: "08:30" });
  });
});
