import { hoje } from "../agendamentos/formatos";

/** Os próximos `n` dias a partir de hoje: data `AAAA-MM-DD` e o texto do botão. */
export function proximosDias(n: number): { data: string; texto: string }[] {
  const [a, m, d] = hoje().split("-").map(Number) as [number, number, number];
  return Array.from({ length: n }, (_, i) => {
    const dia = new Date(a, m - 1, d + i);
    const dois = (x: number) => String(x).padStart(2, "0");
    const data = `${String(dia.getFullYear())}-${dois(dia.getMonth() + 1)}-${dois(dia.getDate())}`;
    const texto = dia
      .toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit" })
      .replace(/^./, (c) => c.toUpperCase());
    return { data, texto: i === 0 ? "Hoje" : i === 1 ? "Amanhã" : texto };
  });
}
