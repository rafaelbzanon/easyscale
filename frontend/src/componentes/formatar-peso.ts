/** "15000.125" → "15.000,125 kg"; "15000.000" → "15.000 kg". Sem passar por número (texto preserva as casas, spec 007 §3.1); só os zeros à direita somem. */
export function formatarPeso(texto: string): string {
  const negativo = texto.startsWith("-");
  const [inteiro = "0", casas = ""] = (negativo ? texto.slice(1) : texto).split(".");
  const decimal = casas.replace(/0+$/, "");
  const agrupado = inteiro.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negativo ? "−" : ""}${agrupado}${decimal ? `,${decimal}` : ""} kg`;
}

/** Idade de um instante em relação a `agora` (ms): "há 4 s", "há 3 min", "há 2 h". */
export function formatarIdade(instante: string, agora: number): string {
  const s = Math.max(0, Math.round((agora - Date.parse(instante)) / 1000));
  if (s < 60) return `há ${String(s)} s`;
  if (s < 3600) return `há ${String(Math.floor(s / 60))} min`;
  return `há ${String(Math.floor(s / 3600))} h`;
}

export const formatarHora = (instante: string) =>
  new Date(instante).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
