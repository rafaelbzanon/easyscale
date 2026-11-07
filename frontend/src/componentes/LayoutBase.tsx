import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { definirAoNaoAutenticado, ErroRequisicao } from "../api/cliente-api";
import { obterEstadoOperacao } from "../api/operacao";
import { encerrarSessao, obterSessaoAtual } from "../api/sessao";
import type { UsuarioAtual } from "../tipos/sessao";
import { Botao } from "./Botao";
import { Cabecalho } from "./Cabecalho";
import { ContextoModo } from "./contexto-modo";
import { MensagemErro } from "./MensagemErro";
import { ITENS_NAVEGACAO } from "./navegacao";
import { nomePerfil } from "./nome-perfil";
import { PlacaModo } from "./PlacaModo";

/** Casca das telas internas: exige sessão e mostra o modo (spec 016 §6.2, §6.4). */
export function LayoutBase() {
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const [sessao, setSessao] = useState<UsuarioAtual | null>(null);
  const [erroSessao, setErroSessao] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);
  const [estado, setEstado] = useState<unknown>(null);

  useEffect(() => {
    definirAoNaoAutenticado(() => void navegar("/login", { replace: true }));
  }, [navegar]);

  useEffect(() => {
    let ativo = true;
    obterSessaoAtual().then(
      (s) => {
        if (ativo) setSessao(s);
      },
      (e: unknown) => {
        if (ativo) setErroSessao(e);
      },
    );
    return () => {
      ativo = false;
    };
  }, [tentativa]);

  const podeConsultarOperacao = sessao?.permissoes.includes("CONSULTAR_OPERACAO") ?? false;
  useEffect(() => {
    if (!podeConsultarOperacao) return;
    let ativo = true;
    // O modo só muda com reinício do backend; a FE-303 o atualiza pelos eventos.
    obterEstadoOperacao().then(
      (e) => {
        if (ativo) setEstado(e);
      },
      () => {
        if (ativo) setEstado(null);
      },
    );
    return () => {
      ativo = false;
    };
  }, [podeConsultarOperacao, pathname]);

  const informarDispositivos = useCallback((dispositivos: unknown) => {
    setEstado({ dispositivos });
  }, []);

  const sair = () => {
    void encerrarSessao()
      .catch(() => undefined)
      .then(() => navegar("/login", { replace: true }));
  };

  const naoAutenticado =
    erroSessao instanceof ErroRequisicao && erroSessao.erro?.codigo === "NAO_AUTENTICADO";

  return (
    <div className="flex min-h-dvh flex-col">
      <Cabecalho>
        {sessao && (
          <>
            <PlacaModo estado={estado} />
            <nav aria-label="Principal" className="flex flex-wrap gap-1">
              {ITENS_NAVEGACAO.filter((item) => sessao.permissoes.includes(item.permissao)).map(
                (item) => (
                  <NavLink
                    key={item.rota}
                    to={item.rota}
                    className={({ isActive }) =>
                      `px-2.5 py-2 text-sm font-semibold ${isActive ? "bg-claro text-tinta" : "text-claro hover:bg-claro/15"}`
                    }
                  >
                    {item.rotulo}
                  </NavLink>
                ),
              )}
            </nav>
            <div className="ml-auto flex items-center gap-3 text-sm">
              <span>
                {sessao.usuario.nome}{" "}
                <span className="hidden text-claro/80 2xl:inline">
                  ({nomePerfil(sessao.usuario.perfil)})
                </span>
              </span>
              <Botao onClick={sair}>Sair</Botao>
            </div>
          </>
        )}
      </Cabecalho>
      <main className="mx-auto w-full max-w-screen-2xl flex-1 px-4 py-6">
        {erroSessao !== null && !naoAutenticado ? (
          <MensagemErro
            erro={erroSessao}
            aoTentarNovamente={() => {
              setErroSessao(null);
              setTentativa((t) => t + 1);
            }}
          />
        ) : sessao ? (
          <ContextoModo value={informarDispositivos}>
            <Outlet context={sessao} />
          </ContextoModo>
        ) : (
          <p className="text-suave">Carregando…</p>
        )}
      </main>
    </div>
  );
}
