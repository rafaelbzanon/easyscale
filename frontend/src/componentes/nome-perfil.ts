const NOMES_PERFIL: Record<string, string> = {
  ADMINISTRADOR: "Administrador",
  OPERADOR: "Operador",
  AUDITOR: "Auditor",
};

/** Perfis novos (RF-031) aparecem com o código, sem tradução. */
export const nomePerfil = (codigo: string) => NOMES_PERFIL[codigo] ?? codigo;
