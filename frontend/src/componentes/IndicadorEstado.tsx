import { SimboloEstado, type TipoEstado } from "./SimboloEstado";

const COR: Record<TipoEstado, string> = {
  falha: "text-vermelho",
  atencao: "text-tinta",
  ok: "text-verde",
  informacao: "text-azul",
};

/** Estado com forma e palavra, nunca só cor (DESIGN.md: Palavra E Forma). */
export function IndicadorEstado({ tipo, texto }: { tipo: TipoEstado; texto: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 font-semibold ${COR[tipo]}`}>
      <SimboloEstado tipo={tipo} />
      {texto}
    </span>
  );
}
