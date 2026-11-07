import type {
  Alteracao,
  FiltrosMotoristas,
  FiltrosProdutos,
  FiltrosTiposVeiculo,
  FiltrosTransportadoras,
  FiltrosVeiculos,
  Motorista,
  MotoristaCriacao,
  Produto,
  ProdutoCriacao,
  TipoVeiculo,
  TipoVeiculoCriacao,
  Transportadora,
  TransportadoraCriacao,
  Veiculo,
  VeiculoCriacao,
} from "../tipos/cadastros";
import { recurso } from "./cliente-api";

// Spec 007 §4.1. Não há DELETE.
export const transportadoras = recurso<
  Transportadora,
  TransportadoraCriacao,
  Alteracao<TransportadoraCriacao>,
  FiltrosTransportadoras
>("/transportadoras");
export const motoristas = recurso<
  Motorista,
  MotoristaCriacao,
  Alteracao<MotoristaCriacao>,
  FiltrosMotoristas
>("/motoristas");
export const tiposVeiculo = recurso<
  TipoVeiculo,
  TipoVeiculoCriacao,
  Alteracao<TipoVeiculoCriacao>,
  FiltrosTiposVeiculo
>("/tipos-veiculo");
export const veiculos = recurso<
  Veiculo,
  VeiculoCriacao,
  Alteracao<VeiculoCriacao>,
  FiltrosVeiculos
>("/veiculos");
export const produtos = recurso<
  Produto,
  ProdutoCriacao,
  Alteracao<ProdutoCriacao>,
  FiltrosProdutos
>("/produtos");
