import { Navigate } from "react-router";
import { ITENS_NAVEGACAO } from "../componentes/navegacao";
import { useSessao } from "../componentes/useSessao";

/** "/" leva à primeira tela do menu que a sessão pode usar. */
export function PaginaInicio() {
  const { permissoes } = useSessao();
  const item = ITENS_NAVEGACAO.find((i) => permissoes.includes(i.permissao));
  if (item) return <Navigate to={item.rota} replace />;
  return <p className="text-suave">Seu perfil não tem acesso a nenhuma tela.</p>;
}
