// Contrato da API de cadastros: spec 007 §5. Decimal trafega como texto (§3.1).

export interface Transportadora {
  id: number;
  ativo: boolean;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string;
  telefone: string | null;
  email: string | null;
}

export interface TransportadoraCriacao {
  razao_social: string;
  nome_fantasia?: string | null;
  cnpj: string;
  telefone?: string | null;
  email?: string | null;
}

export interface Motorista {
  id: number;
  ativo: boolean;
  nome: string;
  /** Completo só para quem tem GERENCIAR_CADASTROS, num item; senão null (§4.2). */
  cpf: string | null;
  cpf_mascarado: string;
  transportadora_id: number | null;
  cnh_numero: string | null;
  cnh_categoria: string | null;
  data_validade_cnh: string | null;
  telefone: string | null;
}

export interface MotoristaCriacao {
  nome: string;
  cpf: string;
  transportadora_id?: number | null;
  cnh_numero?: string | null;
  cnh_categoria?: string | null;
  data_validade_cnh?: string | null;
  telefone?: string | null;
}

export interface TipoVeiculo {
  id: number;
  ativo: boolean;
  descricao: string;
}

export interface TipoVeiculoCriacao {
  descricao: string;
}

export type FormatoPlaca = "ANTIGO" | "MERCOSUL";

export interface Veiculo {
  id: number;
  ativo: boolean;
  placa: string;
  formato_placa: FormatoPlaca;
  tipo_veiculo_id: number;
  transportadora_id: number | null;
  motorista_padrao_id: number | null;
  marca: string | null;
  modelo: string | null;
  eixos: number | null;
  tara_kg: string | null;
  capacidade_kg: string | null;
}

export interface VeiculoCriacao {
  placa: string;
  tipo_veiculo_id: number;
  transportadora_id?: number | null;
  motorista_padrao_id?: number | null;
  marca?: string | null;
  modelo?: string | null;
  eixos?: number | null;
  tara_kg?: string | null;
  capacidade_kg?: string | null;
}

export interface Produto {
  id: number;
  ativo: boolean;
  codigo: string;
  descricao: string;
  unidade: string;
}

export interface ProdutoCriacao {
  codigo: string;
  descricao: string;
  unidade?: string;
}

/** PATCH altera só os campos enviados, inclusive `ativo` (§4.1). */
export type Alteracao<C> = Partial<C> & { ativo?: boolean };

export interface FiltrosTransportadoras {
  ativo?: boolean;
  busca?: string;
}
export interface FiltrosMotoristas {
  ativo?: boolean;
  transportadora_id?: number;
  busca?: string;
}
export interface FiltrosTiposVeiculo {
  ativo?: boolean;
}
export interface FiltrosVeiculos {
  ativo?: boolean;
  transportadora_id?: number;
  placa?: string;
}
export interface FiltrosProdutos {
  ativo?: boolean;
  busca?: string;
}
