// Sessão: spec 012 §5.2.

export interface UsuarioSessao {
  id: number;
  nome: string;
  login: string;
  perfil: string;
}

/** Resposta do login e de GET /api/sessoes/atual. */
export interface UsuarioAtual {
  usuario: UsuarioSessao;
  permissoes: string[];
}

// Usuários e perfis: spec 012 §5.

export interface Login {
  login: string;
  senha: string;
}

export interface Usuario {
  id: number;
  nome: string;
  login: string;
  perfil: string;
  ativo: boolean;
  criado_em: string;
}

export interface UsuarioCriacao {
  nome: string;
  login: string;
  perfil: string;
  senha: string;
}

/** PATCH aceita só `ativo` (§6.5). */
export interface UsuarioAlteracao {
  ativo: boolean;
}

export interface RedefinicaoSenha {
  nova_senha: string;
}

export interface FiltrosUsuarios {
  ativo?: boolean;
  perfil?: string;
  busca?: string;
}

/** GET /api/perfis (§5.4); não paginada. */
export interface ListaPerfis {
  itens: { codigo: string; permissoes: string[] }[];
}
