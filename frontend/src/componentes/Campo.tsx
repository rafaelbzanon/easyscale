import { useId, type InputHTMLAttributes } from "react";

interface PropsCampo extends InputHTMLAttributes<HTMLInputElement> {
  rotulo: string;
  /** Mensagem de erro do campo; marca o campo como inválido. */
  erro?: string | undefined;
}

export const CLASSE_ENTRADA =
  "min-h-10 border border-fio bg-claro px-3 text-tinta aria-invalid:border-2 aria-invalid:border-vermelho";

/** Rótulo, entrada e erro ligados por id. */
export function Campo({ rotulo, erro, className = "", ...props }: PropsCampo) {
  const id = useId();
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className="text-sm font-semibold">
        {rotulo}
      </label>
      <input
        id={id}
        aria-invalid={erro ? true : undefined}
        aria-describedby={erro ? `${id}-erro` : undefined}
        className={CLASSE_ENTRADA}
        {...props}
      />
      {erro && (
        <p id={`${id}-erro`} className="text-sm font-semibold text-vermelho">
          {erro}
        </p>
      )}
    </div>
  );
}
