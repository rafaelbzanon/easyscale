import type { ReactNode } from "react";

/** Cabeçalho asfalto com a faixa amarela de demarcação embaixo. */
export function Cabecalho({
  children,
  titulo,
  grande = false,
}: {
  children?: ReactNode;
  titulo?: string;
  grande?: boolean;
}) {
  return (
    <header className="border-b-4 border-amarelo bg-asfalto text-claro">
      <div
        className={`mx-auto flex max-w-screen-2xl flex-wrap items-center gap-x-4 gap-y-2 px-4 ${grande ? "py-5" : "py-3"}`}
      >
        <p className={`${grande ? "text-3xl" : "text-lg"} font-bold tracking-tight`}>
          EasyScale
          {titulo && <span className="font-normal text-claro/80"> · {titulo}</span>}
        </p>
        {children}
      </div>
    </header>
  );
}
