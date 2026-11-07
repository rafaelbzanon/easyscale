import { useState, type SubmitEvent } from "react";
import { useSearchParams } from "react-router";
import { agendamentos } from "../../api/agendamentos";
import { Abas } from "../../componentes/Abas";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { MensagemErro } from "../../componentes/MensagemErro";
import { SimboloEstado, type TipoEstado } from "../../componentes/SimboloEstado";
import { useCarga } from "../../componentes/useCarga";
import { useSessao } from "../../componentes/useSessao";
import type { Agendamento, StatusAgendamento } from "../../tipos/agendamentos";
import { PainelCadastro } from "../cadastros/PaginaCadastros";
import { CancelarAgendamento } from "./CancelarAgendamento";
import { FAIXAS } from "./faixas";
import { formatarData, hoje } from "./formatos";
import { FormularioAgendamento } from "./FormularioAgendamento";

const STATUS: Record<StatusAgendamento, [string, TipoEstado]> = {
  AGENDADO: ["Agendado", "informacao"],
  EM_ANDAMENTO: ["Em andamento", "informacao"],
  CONCLUIDO: ["Concluído", "ok"],
  CANCELADO: ["Cancelado", "falha"],
  EXPIRADO: ["Expirado", "atencao"],
};

type Acao =
  { tipo: "novo" } | { tipo: "editar"; id: number } | { tipo: "cancelar"; item: Agendamento };

const FILTROS_VAZIOS = {
  data_inicio: hoje(),
  data_fim: "",
  status: "",
  tipo_operacao: "",
  origem: "",
  placa: "",
};

function ListaAgendamentos() {
  const permissoes = useSessao().permissoes;
  const podeCriar = permissoes.includes("CRIAR_AGENDAMENTO");
  const podeGerenciar = permissoes.includes("GERENCIAR_AGENDAMENTOS");
  const [rascunho, setRascunho] = useState(FILTROS_VAZIOS);
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [pagina, setPagina] = useState(1);
  const [acao, setAcao] = useState<Acao | null>(null);
  const [aviso, setAviso] = useState("");

  const lista = useCarga(
    () => {
      // Filtro vazio não vai na consulta (spec 007 §3.3).
      const consulta: Record<string, string | number> = { pagina };
      for (const [nome, valor] of Object.entries(filtros)) if (valor) consulta[nome] = valor;
      return agendamentos.listar(consulta);
    },
    JSON.stringify([filtros, pagina]),
  );
  const paginas = lista.dados
    ? Math.max(1, Math.ceil(lista.dados.total / lista.dados.tamanho_pagina))
    : 1;

  const filtrar = (e: SubmitEvent) => {
    e.preventDefault();
    setFiltros({ ...rascunho, placa: rascunho.placa.trim() });
    setPagina(1);
  };
  const campo = (nome: keyof typeof FILTROS_VAZIOS) => ({
    value: rascunho[nome],
    onChange: (e: { target: { value: string } }) => {
      setRascunho((r) => ({ ...r, [nome]: e.target.value }));
    },
  });
  const concluir = (texto: string) => {
    setAcao(null);
    setAviso(texto);
    lista.recarregar();
  };

  return (
    <section aria-label="Agendamentos">
      <div className="mb-4 flex flex-wrap items-end gap-4">
        <form onSubmit={filtrar} className="flex flex-wrap items-end gap-2">
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Data inicial</span>
            <input type="date" className={CLASSE_ENTRADA} {...campo("data_inicio")} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Data final</span>
            <input type="date" className={CLASSE_ENTRADA} {...campo("data_fim")} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Status</span>
            <select className={CLASSE_ENTRADA} {...campo("status")}>
              <option value="">Todos</option>
              {Object.entries(STATUS).map(([codigo, [texto]]) => (
                <option key={codigo} value={codigo}>
                  {texto}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Tipo</span>
            <select className={CLASSE_ENTRADA} {...campo("tipo_operacao")}>
              <option value="">Todos</option>
              <option value="CARGA">Carga</option>
              <option value="DESCARGA">Descarga</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Origem</span>
            <select className={CLASSE_ENTRADA} {...campo("origem")}>
              <option value="">Todas</option>
              <option value="USUARIO">Usuário</option>
              <option value="AUTOATENDIMENTO">Autoatendimento</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm font-semibold">Placa</span>
            <input className={`${CLASSE_ENTRADA} font-mono`} {...campo("placa")} />
          </label>
          <Botao type="submit">Filtrar</Botao>
        </form>
        {podeCriar && acao === null && (
          <Botao
            variante="acao"
            className="ml-auto"
            onClick={() => {
              setAviso("");
              setAcao({ tipo: "novo" });
            }}
          >
            Novo agendamento
          </Botao>
        )}
      </div>

      {aviso && (
        <p role="status" className="mb-4 flex items-center gap-2 font-semibold">
          <SimboloEstado tipo="ok" />
          {aviso}
        </p>
      )}

      {acao?.tipo === "cancelar" && (
        <CancelarAgendamento
          agendamento={acao.item}
          aoConcluir={() => {
            concluir("Agendamento cancelado.");
          }}
          aoFalhar={lista.recarregar}
          aoVoltar={() => {
            setAcao(null);
          }}
        />
      )}
      {(acao?.tipo === "novo" || acao?.tipo === "editar") && (
        <FormularioAgendamento
          id={acao.tipo === "editar" ? acao.id : null}
          aoVoltar={() => {
            setAcao(null);
          }}
          aoSalvar={(a) => {
            concluir(
              acao.tipo === "novo"
                ? `Agendamento criado: faixa ${a.faixa_hora_inicio}–${a.faixa_hora_fim}.`
                : "Salvo.",
            );
          }}
        />
      )}

      {lista.erro !== undefined ? (
        <MensagemErro erro={lista.erro} aoTentarNovamente={lista.recarregar} />
      ) : !lista.dados ? (
        <p className="text-suave">Carregando…</p>
      ) : lista.dados.itens.length === 0 ? (
        <p className="text-suave">Nenhum agendamento encontrado.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-tinta">
                  {[
                    "Data",
                    "Faixa",
                    "Placa",
                    "Motorista",
                    "Transportadora",
                    "Produto",
                    "Tipo",
                    "Status",
                    "Origem",
                  ].map((c) => (
                    <th key={c} scope="col" className="px-3 py-2 text-sm font-semibold">
                      {c}
                    </th>
                  ))}
                  {podeGerenciar && (
                    <th scope="col" className="px-3 py-2 text-sm font-semibold">
                      Ação
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {lista.dados.itens.map((a) => {
                  const [texto, forma] = STATUS[a.status];
                  return (
                    <tr key={a.id} className="border-b border-fio">
                      <td className="px-3 py-2">{formatarData(a.data_prevista)}</td>
                      <td className="px-3 py-2">
                        {a.faixa_hora_inicio}–{a.faixa_hora_fim}
                      </td>
                      <td className="px-3 py-2 font-mono">{a.placa}</td>
                      <td className="px-3 py-2">{a.motorista_nome}</td>
                      <td className="px-3 py-2">{a.transportadora_razao_social ?? "—"}</td>
                      <td className="px-3 py-2">{a.produto_descricao}</td>
                      <td className="px-3 py-2">
                        {a.tipo_operacao === "CARGA" ? "Carga" : "Descarga"}
                      </td>
                      <td className="px-3 py-2">
                        <span className="inline-flex items-center gap-2 font-semibold">
                          <SimboloEstado tipo={forma} />
                          {texto}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        {a.origem === "USUARIO" ? "Usuário" : "Autoatendimento"}
                      </td>
                      {podeGerenciar && (
                        <td className="px-3 py-2">
                          {a.status === "AGENDADO" && (
                            <span className="flex flex-wrap gap-2">
                              <Botao
                                aria-label={`Editar agendamento de ${a.placa}`}
                                onClick={() => {
                                  setAviso("");
                                  setAcao({ tipo: "editar", id: a.id });
                                }}
                              >
                                Editar
                              </Botao>
                              <Botao
                                aria-label={`Cancelar agendamento de ${a.placa}`}
                                onClick={() => {
                                  setAviso("");
                                  setAcao({ tipo: "cancelar", item: a });
                                }}
                              >
                                Cancelar
                              </Botao>
                            </span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
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
              {lista.dados.total === 1 ? "agendamento" : "agendamentos"}
            </span>
          </nav>
        </>
      )}
    </section>
  );
}

export function PaginaAgendamentos() {
  const [parametros] = useSearchParams();
  const podeFaixas = useSessao().permissoes.includes("CONSULTAR_CADASTROS");
  const faixas = podeFaixas && parametros.get("visao") === "faixas";
  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">Agendamentos</h1>
      {podeFaixas && (
        <Abas
          rotulo="Visão"
          itens={[
            { rotulo: "Agendamentos", para: "?", ativa: !faixas },
            { rotulo: "Faixas de horário", para: "?visao=faixas", ativa: faixas },
          ]}
        />
      )}
      {faixas ? <PainelCadastro def={FAIXAS} /> : <ListaAgendamentos />}
    </section>
  );
}
