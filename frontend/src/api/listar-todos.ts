/** Todas as páginas de um cadastro; o contrato não oferece lista sem paginação (spec 007 §3.3). */
export async function listarTodos<T>(api: {
  listar: (filtros: { pagina: number }) => Promise<{ itens: T[]; total: number }>;
}): Promise<T[]> {
  const itens: T[] = [];
  for (let pagina = 1; ; pagina++) {
    const r = await api.listar({ pagina });
    itens.push(...r.itens);
    if (itens.length >= r.total || r.itens.length === 0) return itens;
  }
}
