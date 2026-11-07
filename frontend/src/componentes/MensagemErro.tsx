import { ErroRequisicao } from "../api/cliente-api";
import { Botao } from "./Botao";
import { SimboloEstado } from "./SimboloEstado";

export function textoErro(erro: unknown): string {
  if (!(erro instanceof ErroRequisicao)) return "Erro inesperado na tela.";
  if (erro.erro === null) return "Sem resposta válida do servidor.";
  if (erro.status === 403 && erro.erro.codigo === "SEM_PERMISSAO") {
    return "Você não tem permissão para esta ação.";
  }
  return erro.erro.mensagem;
}

export function MensagemErro({
  erro,
  texto,
  aoTentarNovamente,
}: {
  erro: unknown;
  /** Texto próprio da tela para este erro; sem ele, vale o texto comum. */
  texto?: string | null;
  aoTentarNovamente?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-wrap items-center gap-3 border border-vermelho bg-claro p-3"
    >
      <SimboloEstado tipo="falha" />
      <p className="font-semibold text-vermelho">{texto ?? textoErro(erro)}</p>
      {aoTentarNovamente && <Botao onClick={aoTentarNovamente}>Tentar de novo</Botao>}
    </div>
  );
}
