import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type {
  Motorista,
  Produto,
  TipoVeiculo,
  Transportadora,
  Veiculo,
} from "../../tipos/cadastros";
import type { UsuarioAtual } from "../../tipos/sessao";
import {
  abrir as abrirTela,
  ADMIN,
  chamadas,
  erro,
  lista,
  OPERADOR,
  servir,
  type Resposta,
  type Rotas,
} from "../../utilitarios-testes";
import { PaginaCadastros } from "./PaginaCadastros";

const TIPO: TipoVeiculo = { id: 1, ativo: true, descricao: "Carreta" };
const TRANSP: Transportadora = {
  id: 5,
  ativo: true,
  razao_social: "Rota Sul Ltda",
  nome_fantasia: null,
  cnpj: "11222333000181",
  telefone: null,
  email: null,
};
const VEICULO: Veiculo = {
  id: 10,
  ativo: true,
  placa: "ABC1D23",
  formato_placa: "MERCOSUL",
  tipo_veiculo_id: 1,
  transportadora_id: 5,
  motorista_padrao_id: null,
  marca: "Scania",
  modelo: null,
  eixos: 6,
  tara_kg: "15000.500",
  capacidade_kg: null,
};
const MOTORISTA_LISTA: Motorista = {
  id: 20,
  ativo: true,
  nome: "João Lima",
  cpf: null,
  cpf_mascarado: "***.456.789-**",
  transportadora_id: null,
  cnh_numero: null,
  cnh_categoria: null,
  data_validade_cnh: null,
  telefone: null,
};
const PRODUTO: Produto = {
  id: 30,
  ativo: true,
  codigo: "SOJA",
  descricao: "Soja em grão",
  unidade: "KG",
};

const APOIO: Rotas = {
  "GET /api/tipos-veiculo?pagina=1": [200, lista([TIPO])],
  "GET /api/transportadoras?pagina=1": [200, lista([TRANSP])],
  "GET /api/motoristas?pagina=1": [200, lista([MOTORISTA_LISTA])],
};

function abrir(rota: string, quem: UsuarioAtual = ADMIN) {
  abrirTela(rota, "cadastros", <PaginaCadastros />, quem);
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("CA-001: lista e abas", () => {
  it("lista veículos ativos com nomes dos cadastros ligados e troca de aba", async () => {
    const f = servir({
      ...APOIO,
      "GET /api/veiculos?ativo=true&pagina=1": [200, lista([VEICULO])],
      "GET /api/produtos?ativo=true&pagina=1": [200, lista([PRODUTO])],
    });
    abrir("/cadastros");
    const linha = (await screen.findByText("ABC1D23")).closest("tr");
    expect(linha).not.toBeNull();
    const dentro = within(linha as HTMLElement);
    expect(dentro.getByText("Carreta")).toBeInTheDocument();
    expect(dentro.getByText("Rota Sul Ltda")).toBeInTheDocument();
    expect(dentro.getByText("Ativo")).toBeInTheDocument();
    expect(f.mock.calls.some(([u]) => u === "/api/veiculos?ativo=true&pagina=1")).toBe(true);

    await userEvent.click(screen.getByRole("link", { name: "Produtos" }));
    expect(await screen.findByText("Soja em grão")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Produtos" })).toHaveAttribute("aria-current", "page");
  });

  it("mostra Inativo com palavra e filtra por situação", async () => {
    const f = servir({
      ...APOIO,
      "GET /api/veiculos?ativo=true&pagina=1": [200, lista([])],
      "GET /api/veiculos?pagina=1": [200, lista([{ ...VEICULO, ativo: false }])],
    });
    abrir("/cadastros?recurso=veiculos");
    expect(await screen.findByText("Nenhum cadastro encontrado.")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Situação"), "todos");
    expect(await screen.findByText("Inativo")).toBeInTheDocument();
    expect(f.mock.calls.some(([u]) => u === "/api/veiculos?pagina=1")).toBe(true);
  });
});

describe("CA-002: CPF", () => {
  it("lista só o CPF mascarado", async () => {
    servir({
      "GET /api/transportadoras?pagina=1": [200, lista([TRANSP])],
      "GET /api/motoristas?ativo=true&pagina=1": [200, lista([MOTORISTA_LISTA])],
    });
    abrir("/cadastros?recurso=motoristas");
    expect(await screen.findByText("***.456.789-**")).toBeInTheDocument();
  });
});

describe("CA-003: sem GERENCIAR_CADASTROS", () => {
  it("operador só consulta", async () => {
    servir({ ...APOIO, "GET /api/veiculos?ativo=true&pagina=1": [200, lista([VEICULO])] });
    abrir("/cadastros", OPERADOR);
    await screen.findByText("ABC1D23");
    expect(screen.queryByRole("button", { name: /Novo/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Editar/ })).not.toBeInTheDocument();
  });
});

describe("CA-004, CA-010: criar", () => {
  it("envia só o preenchido, com a placa digitada, e mostra Salvo só depois do sucesso", async () => {
    let criado = false;
    const f = servir({
      ...APOIO,
      "GET /api/veiculos?ativo=true&pagina=1": () => [200, lista(criado ? [VEICULO] : [])],
      "POST /api/veiculos": () => {
        criado = true;
        return [201, VEICULO];
      },
    });
    abrir("/cadastros?recurso=veiculos");
    await userEvent.click(await screen.findByRole("button", { name: "Novo veículo" }));
    await userEvent.type(screen.getByLabelText("Placa (obrigatório)"), "abc-1d23");
    await userEvent.selectOptions(
      screen.getByLabelText("Tipo de veículo (obrigatório)"),
      "Carreta",
    );
    await userEvent.type(screen.getByLabelText("Tara (kg)"), "15000,5");
    expect(screen.queryByText("Salvo.")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByText("Salvo.")).toBeInTheDocument();
    expect(JSON.parse(chamadas(f, "POST")[0]?.[1]?.body as string)).toEqual({
      placa: "abc-1d23",
      tipo_veiculo_id: 1,
      tara_kg: "15000.5",
    });
    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Novo veículo" })).not.toBeInTheDocument();
  });

  it("tira a máscara de CNPJ e telefone", async () => {
    const f = servir({
      "GET /api/transportadoras?ativo=true&pagina=1": [200, lista([])],
      "POST /api/transportadoras": [201, TRANSP],
    });
    abrir("/cadastros?recurso=transportadoras");
    await userEvent.click(await screen.findByRole("button", { name: "Nova transportadora" }));
    await userEvent.type(screen.getByLabelText("Razão social (obrigatório)"), "Rota Sul Ltda");
    await userEvent.type(screen.getByLabelText("CNPJ (obrigatório)"), "11.222.333/0001-81");
    await userEvent.type(screen.getByLabelText("Telefone"), "(54) 3000-1234");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await screen.findByText("Salvo.");
    expect(JSON.parse(chamadas(f, "POST")[0]?.[1]?.body as string)).toEqual({
      razao_social: "Rota Sul Ltda",
      cnpj: "11222333000181",
      telefone: "5430001234",
    });
  });
});

describe("CA-005, CA-006: editar e desativar", () => {
  const rotasVeiculo: Rotas = {
    ...APOIO,
    "GET /api/veiculos?ativo=true&pagina=1": [200, lista([VEICULO])],
    "GET /api/veiculos/10": [200, VEICULO],
  };

  it("PATCH leva só o campo alterado", async () => {
    const f = servir({
      ...rotasVeiculo,
      "PATCH /api/veiculos/10": [200, { ...VEICULO, marca: "Volvo" }],
    });
    abrir("/cadastros?recurso=veiculos");
    await userEvent.click(await screen.findByRole("button", { name: "Editar ABC1D23" }));
    const marca = await screen.findByLabelText("Marca");
    expect(marca).toHaveValue("Scania");
    await userEvent.clear(marca);
    await userEvent.type(marca, "Volvo");
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await screen.findByText("Salvo.");
    expect(JSON.parse(chamadas(f, "PATCH")[0]?.[1]?.body as string)).toEqual({ marca: "Volvo" });
  });

  it("limpar campo opcional envia null; sem alteração não envia nada", async () => {
    const f = servir({ ...rotasVeiculo, "PATCH /api/veiculos/10": [200, VEICULO] });
    abrir("/cadastros?recurso=veiculos");
    await userEvent.click(await screen.findByRole("button", { name: "Editar ABC1D23" }));
    await userEvent.click(await screen.findByRole("button", { name: "Salvar" }));
    expect(chamadas(f, "PATCH")).toHaveLength(0);
    expect(screen.queryByRole("heading", { name: /Editar/ })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Editar ABC1D23" }));
    await userEvent.clear(await screen.findByLabelText("Marca"));
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await screen.findByText("Salvo.");
    expect(JSON.parse(chamadas(f, "PATCH")[0]?.[1]?.body as string)).toEqual({ marca: null });
  });

  it("administrador vê o CPF completo no formulário, e só ali", async () => {
    servir({
      "GET /api/transportadoras?pagina=1": [200, lista([TRANSP])],
      "GET /api/motoristas?ativo=true&pagina=1": [200, lista([MOTORISTA_LISTA])],
      "GET /api/motoristas/20": [200, { ...MOTORISTA_LISTA, cpf: "12345678909" }],
    });
    abrir("/cadastros?recurso=motoristas");
    await userEvent.click(await screen.findByRole("button", { name: "Editar João Lima" }));
    expect(await screen.findByLabelText("CPF (obrigatório)")).toHaveValue("12345678909");
  });

  it("desativar mostra o aviso e envia ativo false", async () => {
    const f = servir({
      ...rotasVeiculo,
      "PATCH /api/veiculos/10": [200, { ...VEICULO, ativo: false }],
    });
    abrir("/cadastros?recurso=veiculos");
    await userEvent.click(await screen.findByRole("button", { name: "Editar ABC1D23" }));
    await userEvent.click(await screen.findByLabelText("Cadastro ativo"));
    expect(screen.getByText(/não é autorizado na entrada/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar e desativar" }));
    await screen.findByText("Salvo.");
    expect(JSON.parse(chamadas(f, "PATCH")[0]?.[1]?.body as string)).toEqual({ ativo: false });
  });
});

describe("CA-007, CA-008: recusa no envio", () => {
  async function tentarCriarVeiculo(resposta: Resposta) {
    const f = servir({
      ...APOIO,
      "GET /api/veiculos?ativo=true&pagina=1": [200, lista([])],
      "POST /api/veiculos": resposta,
    });
    abrir("/cadastros?recurso=veiculos");
    await userEvent.click(await screen.findByRole("button", { name: "Novo veículo" }));
    await userEvent.type(screen.getByLabelText("Placa (obrigatório)"), "ABC1234");
    await userEvent.selectOptions(
      screen.getByLabelText("Tipo de veículo (obrigatório)"),
      "Carreta",
    );
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }));
    return f;
  }

  it("409 mantém o formulário, os dados e marca o campo", async () => {
    await tentarCriarVeiculo([
      409,
      erro("CONFLITO", "Já existe um veículo com esta placa.", [
        { campo: "placa", codigo: "PLACA_DUPLICADA" },
      ]),
    ]);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Já existe um veículo com esta placa.",
    );
    const placa = screen.getByLabelText("Placa (obrigatório)");
    expect(placa).toHaveValue("ABC1234");
    expect(placa).toHaveAttribute("aria-invalid", "true");
    expect(screen.queryByText("Salvo.")).not.toBeInTheDocument();
  });

  it("422 PLACA_INVALIDA explica o campo", async () => {
    await tentarCriarVeiculo([
      422,
      erro("CAMPO_INVALIDO", "Dados inválidos.", [{ campo: "placa", codigo: "PLACA_INVALIDA" }]),
    ]);
    expect(await screen.findByText(/Placa inválida/)).toBeInTheDocument();
  });

  it.each<[string, Resposta, string]>([
    ["403", [403, erro("SEM_PERMISSAO", "x")], "Você não tem permissão para esta ação."],
    ["500", [500, erro("ERRO_INTERNO", "Erro interno.")], "Erro interno."],
    ["rede caída", "rede", "Sem resposta válida do servidor."],
  ])("%s mostra erro e não fecha o formulário", async (_nome, resposta, texto) => {
    await tentarCriarVeiculo(resposta);
    expect(await screen.findByRole("alert")).toHaveTextContent(texto);
    expect(screen.getByRole("heading", { name: "Novo veículo" })).toBeInTheDocument();
    expect(screen.queryByText("Salvo.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar" })).toBeEnabled();
  });
});

describe("CA-009: falha ao listar", () => {
  it("mostra o erro e tenta de novo", async () => {
    let falhou = true;
    servir({
      ...APOIO,
      "GET /api/veiculos?ativo=true&pagina=1": () =>
        falhou ? [500, erro("ERRO_INTERNO", "Erro interno.")] : [200, lista([VEICULO])],
    });
    abrir("/cadastros?recurso=veiculos");
    expect(await screen.findByRole("alert")).toHaveTextContent("Erro interno.");
    falhou = false;
    await userEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(await screen.findByText("ABC1D23")).toBeInTheDocument();
  });
});

describe("CA-011: paginação", () => {
  it("Próxima pede a página seguinte", async () => {
    const f = servir({
      "GET /api/produtos?ativo=true&pagina=1": [
        200,
        lista([PRODUTO], { total: 2, tamanho_pagina: 1 }),
      ],
      "GET /api/produtos?ativo=true&pagina=2": [
        200,
        lista([{ ...PRODUTO, id: 31, descricao: "Milho" }], {
          total: 2,
          tamanho_pagina: 1,
          pagina: 2,
        }),
      ],
    });
    abrir("/cadastros?recurso=produtos");
    expect(await screen.findByText("Página 1 de 2 · 2 cadastros")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    expect(await screen.findByText("Milho")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
    });
    expect(f.mock.calls.some(([u]) => u === "/api/produtos?ativo=true&pagina=2")).toBe(true);
  });
});
