// Formas da ISO 7010: triângulo atenção, círculo cortado falha, quadrado ok, círculo cheio ação/informação.
export type TipoEstado = "atencao" | "falha" | "ok" | "informacao";

export function SimboloEstado({ tipo }: { tipo: TipoEstado }) {
  return (
    <svg viewBox="0 0 16 16" className="size-[1em] shrink-0" aria-hidden="true">
      {tipo === "atencao" && (
        <path d="M8 1.5 15 14.5H1Z" className="fill-amarelo stroke-tinta" strokeWidth="1.2" />
      )}
      {tipo === "falha" && (
        <>
          <circle cx="8" cy="8" r="6.2" className="fill-none stroke-vermelho" strokeWidth="2.4" />
          <path d="M3.6 12.4 12.4 3.6" className="stroke-vermelho" strokeWidth="2.4" />
        </>
      )}
      {tipo === "ok" && <rect x="2" y="2" width="12" height="12" className="fill-verde" />}
      {tipo === "informacao" && <circle cx="8" cy="8" r="6.5" className="fill-azul" />}
    </svg>
  );
}
