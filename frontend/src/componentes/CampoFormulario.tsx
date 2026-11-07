import type { ReactNode } from "react";

/** Rótulo, controle (input, select) e mensagem do campo. A mensagem vem do backend (spec 007 §3.2). */
export function CampoFormulario({
  rotulo,
  obrigatorio = false,
  erro,
  children,
}: {
  rotulo: string;
  obrigatorio?: boolean | undefined;
  erro?: string | undefined;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="flex flex-col gap-1">
        <span className="text-sm font-semibold">
          {rotulo}
          {obrigatorio && <span className="font-normal text-suave"> (obrigatório)</span>}
        </span>
        {children}
      </label>
      {erro && <p className="text-sm font-semibold text-vermelho">{erro}</p>}
    </div>
  );
}
