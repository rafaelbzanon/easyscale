import { useState, type SubmitEvent } from "react";
import { useSearchParams } from "react-router";
import { listarTodos } from "../../api/listar-todos";
import { Abas } from "../../componentes/Abas";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { MensagemErro } from "../../componentes/MensagemErro";
import { SimboloEstado } from "../../componentes/SimboloEstado";
import { useCarga } from "../../componentes/useCarga";
import { useSessao } from "../../componentes/useSessao";
import { APOIOS, CADASTROS, type Apoio, type DefCadastro } from "./definicoes";
import { FormularioCadastro, type Opcoes } from "./FormularioCadastro";

type Situacao = "ativos" | "inativos" | "todos";
const ATIVO_DA_SITUACAO = { ativos: true, inativos: false, todos: undefined };

function Situacao({ ativo }: { ativo: boolean }) {
  return (
    <span className="inline-flex items-center gap-2 font-semibold">
      <SimboloEstado tipo={ativo ? "ok" : "atencao"} />
      {ativo ? "Ativo" : "Inativo"}
    </span>
  );
}

export function PainelCadastro({ def }: { def: DefCadastro }) {
  const podeGerenciar = useSessao().permissoes.includes("GERENCIAR_CADASTROS");
  const [situacao, setSituacao] = useState<Situacao>("ativos");
  const [rascunho, setRascunho] = useState("");
  const [busca, setBusca] = useState("");
  const [pagina, setPagina] = useState(1);
  // `undefined`: formulário fechado; `null`: novo; número: editar esse id.
  const [editando, setEditando] = useState<number | null | undefined>(undefined);
  const [salvo, setSalvo] = useState(false);

  const apoiosUsados = [
    ...new Set(def.campos.flatMap((c) => (c.tipo && c.tipo in APOIOS ? [c.tipo as Apoio] : []))),
  ];
  const apoios = useCarga(async () => {
    const lista = await Promise.all(apoiosUsados.map((a) => listarTodos(APOIOS[a].api)));
    return Object.fromEntries(apoiosUsados.map((a, i) => [a, lista[i]]));
  }, def.chave);
  const opcoes: Opcoes = { transportadoras: [], tiposVeiculo: [], motoristas: [], ...apoios.dados };
  const rotuloApoio = (apoio: Apoio, id: unknown) => {
    const item = opcoes[apoio].find((i) => i.id === id);
    return item ? APOIOS[apoio].rotulo(item) : "—";
  };

  const lista = useCarga(
    () =>
      def.api.listar({
        ativo: ATIVO_DA_SITUACAO[situacao],
        ...(def.busca && busca ? { [def.busca.parametro]: busca } : {}),
        pagina,
      }),
    `${def.chave}/${situacao}/${busca}/${String(pagina)}`,
  );

  const buscar = (e: SubmitEvent) => {
    e.preventDefault();
    setBusca(rascunho.trim());
    setPagina(1);
  };

  const paginas = lista.dados
    ? Math.max(1, Math.ceil(lista.dados.total / lista.dados.tamanho_pagina))
    : 1;

  return (
    <section aria-label={def.rotulo}>
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <form onSubmit={buscar} className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Situação</span>
            <select
              className={CLASSE_ENTRADA}
              value={situacao}
              onChange={(e) => {
                setSituacao(e.target.value as Situacao);
                setPagina(1);
              }}
            >
              <option value="ativos">Ativos</option>
              <option value="inativos">Inativos</option>
              <option value="todos">Todos</option>
            </select>
          </label>
          {def.busca && (
            <label className="flex flex-col gap-1">
              <span className="text-sm font-semibold">{def.busca.rotulo}</span>
              <input
                className={CLASSE_ENTRADA}
                value={rascunho}
                onChange={(e) => {
                  setRascunho(e.target.value);
                }}
              />
            </label>
          )}
          {def.busca && <Botao type="submit">Buscar</Botao>}
        </form>
        {podeGerenciar && editando === undefined && (
          <Botao
            variante="acao"
            className="ml-auto"
            onClick={() => {
              setSalvo(false);
              setEditando(null);
            }}
          >
            {def.novo}
          </Botao>
        )}
      </div>

      {salvo && (
        <p role="status" className="mb-4 flex items-center gap-2 font-semibold">
          <SimboloEstado tipo="ok" />
          Salvo.
        </p>
      )}

      {editando !== undefined &&
        (apoios.erro !== undefined ? (
          <div className="mb-6">
            <MensagemErro erro={apoios.erro} aoTentarNovamente={apoios.recarregar} />
          </div>
        ) : apoios.carregando ? (
          <p className="mb-6 text-suave">Carregando…</p>
        ) : (
          <FormularioCadastro
            def={def}
            id={editando}
            opcoes={opcoes}
            aoCancelar={() => {
              setEditando(undefined);
            }}
            aoSalvar={() => {
              setEditando(undefined);
              setSalvo(true);
              lista.recarregar();
              apoios.recarregar();
            }}
          />
        ))}

      {lista.erro !== undefined ? (
        <MensagemErro erro={lista.erro} aoTentarNovamente={lista.recarregar} />
      ) : lista.carregando || !lista.dados ? (
        <p className="text-suave">Carregando…</p>
      ) : lista.dados.itens.length === 0 ? (
        <p className="text-suave">Nenhum cadastro encontrado.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-tinta">
                  {def.colunas.map((c) => (
                    <th key={c.rotulo} scope="col" className="px-3 py-2 text-sm font-semibold">
                      {c.rotulo}
                    </th>
                  ))}
                  <th scope="col" className="px-3 py-2 text-sm font-semibold">
                    Situação
                  </th>
                  {podeGerenciar && (
                    <th scope="col" className="px-3 py-2 text-sm font-semibold">
                      Ação
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {lista.dados.itens.map((item) => (
                  <tr key={item.id} className="border-b border-fio">
                    {def.colunas.map((c) => (
                      <td key={c.rotulo} className={`px-3 py-2 ${c.mono ? "font-mono" : ""}`}>
                        {c.valor(item, rotuloApoio)}
                      </td>
                    ))}
                    <td className="px-3 py-2">
                      <Situacao ativo={item.ativo} />
                    </td>
                    {podeGerenciar && (
                      <td className="px-3 py-2">
                        <Botao
                          aria-label={`Editar ${def.colunas[0]?.valor(item, rotuloApoio) ?? ""}`}
                          onClick={() => {
                            setSalvo(false);
                            setEditando(item.id);
                          }}
                        >
                          Editar
                        </Botao>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav aria-label="Paginação" className="mt-4 flex flex-wrap items-center gap-3">
            <Botao
              disabled={pagina <= 1}
              onClick={() => {
                setPagina(pagina - 1);
              }}
            >
              Anterior
            </Botao>
            <Botao
              disabled={pagina >= paginas}
              onClick={() => {
                setPagina(pagina + 1);
              }}
            >
              Próxima
            </Botao>
            <span className="text-sm text-suave">
              Página {pagina} de {paginas} · {lista.dados.total}{" "}
              {lista.dados.total === 1 ? "cadastro" : "cadastros"}
            </span>
          </nav>
        </>
      )}
    </section>
  );
}

export function PaginaCadastros() {
  const [parametros] = useSearchParams();
  const def = CADASTROS.find((c) => c.chave === parametros.get("recurso")) ?? CADASTROS[0];
  if (!def) return null;
  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">Cadastros</h1>
      <Abas
        rotulo="Tipo de cadastro"
        itens={CADASTROS.map((c) => ({
          rotulo: c.rotulo,
          para: `?recurso=${c.chave}`,
          ativa: c.chave === def.chave,
        }))}
      />
      <PainelCadastro key={def.chave} def={def} />
    </section>
  );
}
