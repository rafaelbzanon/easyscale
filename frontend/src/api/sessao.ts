import type { Lista, Paginacao } from "../tipos/comum";
import type {
  FiltrosUsuarios,
  ListaPerfis,
  Login,
  RedefinicaoSenha,
  Usuario,
  UsuarioAlteracao,
  UsuarioAtual,
  UsuarioCriacao,
} from "../tipos/sessao";
import { comQuery, requisitar } from "./cliente-api";

// Spec 012 §4.
export const entrar = (dados: Login) => requisitar<UsuarioAtual>("POST", "/sessoes", dados);
export const obterSessaoAtual = () => requisitar<UsuarioAtual>("GET", "/sessoes/atual");
/** Sempre 204, com ou sem sessão (§6.4). */
export const encerrarSessao = () => requisitar<undefined>("DELETE", "/sessoes/atual");

export const usuarios = {
  listar: (filtros: FiltrosUsuarios & Paginacao = {}) =>
    requisitar<Lista<Usuario>>("GET", comQuery("/usuarios", { ...filtros })),
  obter: (id: number) => requisitar<Usuario>("GET", `/usuarios/${String(id)}`),
  criar: (dados: UsuarioCriacao) => requisitar<Usuario>("POST", "/usuarios", dados),
  alterar: (id: number, dados: UsuarioAlteracao) =>
    requisitar<Usuario>("PATCH", `/usuarios/${String(id)}`, dados),
  redefinirSenha: (id: number, dados: RedefinicaoSenha) =>
    requisitar<undefined>("POST", `/usuarios/${String(id)}/redefinir-senha`, dados),
};

export const listarPerfis = () => requisitar<ListaPerfis>("GET", "/perfis");
