import type { ButtonHTMLAttributes } from "react";

interface PropsBotao extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: "acao" | "neutro";
}

// Azul só para a ação disponível agora (surface brief); o resto é neutro.
const VARIANTES = {
  acao: "bg-azul text-claro border-azul hover:bg-tinta hover:border-tinta",
  neutro: "bg-transparent text-current border-current hover:bg-current/15",
};

export function Botao({ variante = "neutro", className = "", ...props }: PropsBotao) {
  return (
    <button
      type="button"
      className={`inline-flex min-h-10 items-center gap-2 border px-4 text-sm font-semibold transition-colors duration-150 disabled:cursor-not-allowed disabled:border-fio disabled:bg-painel disabled:text-suave ${VARIANTES[variante]} ${className}`}
      {...props}
    />
  );
}
