// Regras comuns da API: spec 007 §3.

export interface CampoErro {
  campo: string;
  codigo: string;
}

/** Corpo de toda resposta de erro (spec 007 §3.2). */
export interface ErroApi {
  erro: {
    codigo: string;
    mensagem: string;
    campos: CampoErro[];
  };
}

/** Resposta paginada (spec 007 §3.3). */
export interface Lista<T> {
  itens: T[];
  total: number;
  pagina: number;
  tamanho_pagina: number;
}

/** Paginação das listas (spec 007 §3.3). */
export interface Paginacao {
  pagina?: number;
  tamanho_pagina?: number;
}
