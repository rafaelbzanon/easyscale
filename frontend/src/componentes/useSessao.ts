import { useOutletContext } from "react-router";
import type { UsuarioAtual } from "../tipos/sessao";

/** Sessão carregada pelo LayoutBase. Só para esconder o que o usuário não pode usar (S-5). */
export function useSessao(): UsuarioAtual {
  return useOutletContext<UsuarioAtual>();
}
