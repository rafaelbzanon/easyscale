import { motoristas, produtos, tiposVeiculo, transportadoras, veiculos } from "../../api/cadastros";
import type { Lista } from "../../tipos/comum";

/** Item de qualquer cadastro; os campos próprios de cada um vêm de `tipos/cadastros.ts`. */
export type Registro = { id: number; ativo: boolean } & Record<string, unknown>;

export interface ApiCadastro {
  listar: (
    filtros: Record<string, string | number | boolean | undefined>,
  ) => Promise<Lista<Registro>>;
  obter: (id: number) => Promise<Registro>;
  criar: (dados: Record<string, unknown>) => Promise<Registro>;
  alterar: (id: number, dados: Record<string, unknown>) => Promise<Registro>;
}

export type Apoio = "transportadoras" | "tiposVeiculo" | "motoristas";

export interface DefCampo {
  nome: string;
  rotulo: string;
  tipo?: "texto" | "numero" | "data" | "hora" | "email" | Apoio;
  obrigatorio?: boolean;
  max?: number;
  /** Tira a máscara antes de enviar (spec 018 §6.2 item 4). */
  limpar?: (v: string) => string;
}

export interface DefColuna {
  rotulo: string;
  valor: (item: Registro, rotulo: (apoio: Apoio, id: unknown) => string) => string;
  mono?: boolean;
}

export interface DefCadastro {
  chave: string;
  rotulo: string;
  novo: string;
  api: ApiCadastro;
  campos: DefCampo[];
  /** Aviso ao desmarcar "ativo" (spec 018 §6.3). */
  avisoInativo?: string;
  colunas: DefColuna[];
  /** Nome do filtro de texto no contrato, se houver (spec 007 §5). */
  busca?: { parametro: "busca" | "placa"; rotulo: string };
}

// Cast: os recursos são tipados por cadastro em api/cadastros.ts; aqui a tela os trata de forma única.
const api = (recurso: unknown) => recurso as ApiCadastro;

const digitos = (v: string) => v.replace(/\D/g, "");
const cnpj = (v: string) => v.replace(/[.\-/\s]/g, "").toUpperCase();
const decimal = (v: string) => v.replace(",", ".");
export const emTexto = (v: unknown): string =>
  typeof v === "string" ? v : typeof v === "number" ? String(v) : "";
const ou = (v: unknown) => emTexto(v) || "—";

export const CADASTROS: DefCadastro[] = [
  {
    chave: "veiculos",
    rotulo: "Veículos",
    novo: "Novo veículo",
    api: api(veiculos),
    busca: { parametro: "placa", rotulo: "Placa" },
    campos: [
      { nome: "placa", rotulo: "Placa", obrigatorio: true, max: 8 },
      {
        nome: "tipo_veiculo_id",
        rotulo: "Tipo de veículo",
        tipo: "tiposVeiculo",
        obrigatorio: true,
      },
      { nome: "transportadora_id", rotulo: "Transportadora", tipo: "transportadoras" },
      { nome: "motorista_padrao_id", rotulo: "Motorista padrão", tipo: "motoristas" },
      { nome: "marca", rotulo: "Marca", max: 30 },
      { nome: "modelo", rotulo: "Modelo", max: 30 },
      { nome: "eixos", rotulo: "Eixos", tipo: "numero" },
      { nome: "tara_kg", rotulo: "Tara (kg)", limpar: decimal },
      { nome: "capacidade_kg", rotulo: "Capacidade (kg)", limpar: decimal },
    ],
    colunas: [
      { rotulo: "Placa", valor: (i) => emTexto(i.placa), mono: true },
      { rotulo: "Tipo", valor: (i, r) => r("tiposVeiculo", i.tipo_veiculo_id) },
      { rotulo: "Transportadora", valor: (i, r) => r("transportadoras", i.transportadora_id) },
      { rotulo: "Motorista padrão", valor: (i, r) => r("motoristas", i.motorista_padrao_id) },
      {
        rotulo: "Marca e modelo",
        valor: (i) => [i.marca, i.modelo].filter(Boolean).join(" ") || "—",
      },
      { rotulo: "Eixos", valor: (i) => ou(i.eixos) },
      { rotulo: "Tara (kg)", valor: (i) => ou(i.tara_kg) },
      { rotulo: "Capacidade (kg)", valor: (i) => ou(i.capacidade_kg) },
    ],
  },
  {
    chave: "motoristas",
    rotulo: "Motoristas",
    novo: "Novo motorista",
    api: api(motoristas),
    busca: { parametro: "busca", rotulo: "Nome" },
    campos: [
      { nome: "nome", rotulo: "Nome", obrigatorio: true, max: 100 },
      { nome: "cpf", rotulo: "CPF", obrigatorio: true, max: 14, limpar: digitos },
      { nome: "transportadora_id", rotulo: "Transportadora", tipo: "transportadoras" },
      { nome: "cnh_numero", rotulo: "Número da CNH", max: 20 },
      { nome: "cnh_categoria", rotulo: "Categoria da CNH", max: 2 },
      { nome: "data_validade_cnh", rotulo: "Validade da CNH", tipo: "data" },
      { nome: "telefone", rotulo: "Telefone", max: 20, limpar: digitos },
    ],
    colunas: [
      { rotulo: "Nome", valor: (i) => emTexto(i.nome) },
      { rotulo: "CPF", valor: (i) => emTexto(i.cpf_mascarado), mono: true },
      { rotulo: "Transportadora", valor: (i, r) => r("transportadoras", i.transportadora_id) },
      {
        rotulo: "CNH",
        valor: (i) => [i.cnh_numero, i.cnh_categoria].filter(Boolean).join(" ") || "—",
      },
      { rotulo: "Validade da CNH", valor: (i) => ou(i.data_validade_cnh) },
      { rotulo: "Telefone", valor: (i) => ou(i.telefone) },
    ],
  },
  {
    chave: "transportadoras",
    rotulo: "Transportadoras",
    novo: "Nova transportadora",
    api: api(transportadoras),
    busca: { parametro: "busca", rotulo: "Razão social ou nome fantasia" },
    campos: [
      { nome: "razao_social", rotulo: "Razão social", obrigatorio: true, max: 100 },
      { nome: "nome_fantasia", rotulo: "Nome fantasia", max: 100 },
      { nome: "cnpj", rotulo: "CNPJ", obrigatorio: true, max: 18, limpar: cnpj },
      { nome: "telefone", rotulo: "Telefone", max: 20, limpar: digitos },
      { nome: "email", rotulo: "E-mail", tipo: "email", max: 100 },
    ],
    colunas: [
      { rotulo: "Razão social", valor: (i) => emTexto(i.razao_social) },
      { rotulo: "Nome fantasia", valor: (i) => ou(i.nome_fantasia) },
      { rotulo: "CNPJ", valor: (i) => emTexto(i.cnpj), mono: true },
      { rotulo: "Telefone", valor: (i) => ou(i.telefone) },
      { rotulo: "E-mail", valor: (i) => ou(i.email) },
    ],
  },
  {
    chave: "tipos-veiculo",
    rotulo: "Tipos de veículo",
    novo: "Novo tipo de veículo",
    api: api(tiposVeiculo),
    campos: [{ nome: "descricao", rotulo: "Descrição", obrigatorio: true, max: 100 }],
    colunas: [{ rotulo: "Descrição", valor: (i) => emTexto(i.descricao) }],
  },
  {
    chave: "produtos",
    rotulo: "Produtos",
    novo: "Novo produto",
    api: api(produtos),
    busca: { parametro: "busca", rotulo: "Código ou descrição" },
    campos: [
      { nome: "codigo", rotulo: "Código", obrigatorio: true, max: 30 },
      { nome: "descricao", rotulo: "Descrição", obrigatorio: true, max: 100 },
      { nome: "unidade", rotulo: "Unidade", max: 5 },
    ],
    colunas: [
      { rotulo: "Código", valor: (i) => emTexto(i.codigo), mono: true },
      { rotulo: "Descrição", valor: (i) => emTexto(i.descricao) },
      { rotulo: "Unidade", valor: (i) => ou(i.unidade) },
    ],
  },
];

/** Cadastros de apoio das listas de escolha (rótulo de cada item). */
export const APOIOS: Record<Apoio, { api: ApiCadastro; rotulo: (i: Registro) => string }> = {
  transportadoras: { api: api(transportadoras), rotulo: (i) => emTexto(i.razao_social) },
  tiposVeiculo: { api: api(tiposVeiculo), rotulo: (i) => emTexto(i.descricao) },
  motoristas: { api: api(motoristas), rotulo: (i) => emTexto(i.nome) },
};
