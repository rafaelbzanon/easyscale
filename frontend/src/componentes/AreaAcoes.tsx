import type { ReactNode } from "react";
import { SimboloEstado } from "./SimboloEstado";

/** Envolve os botões de ação; bloqueada, desabilita todos (ADR-0005 §4, spec 016 §6.5). */
export function AreaAcoes({ bloqueada, children }: { bloqueada: boolean; children: ReactNode }) {
  return (
    <section aria-label="Ações" className="border-t border-fio">
      {bloqueada && (
        <div role="alert" className="faixa-zebrada flex justify-center py-2">
          <p className="flex items-center gap-2 bg-amarelo px-3 py-1 text-sm font-bold text-tinta">
            <SimboloEstado tipo="atencao" />
            Tela desatualizada. Ações bloqueadas até reconectar.
          </p>
        </div>
      )}
      <fieldset disabled={bloqueada} className="flex flex-wrap gap-2 py-3">
        {children}
      </fieldset>
    </section>
  );
}
