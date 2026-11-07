import { useState, type SubmitEvent } from "react";
import { listarPesagens } from "../../api/historico";
import { ErroRequisicao } from "../../api/cliente-api";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { MensagemErro } from "../../componentes/MensagemErro";
import { textoCodigo } from "../../componentes/texto-codigo";
import { useCarga } from "../../componentes/useCarga";
import { formatarPeso } from "../../componentes/formatar-peso";
import type { Pesagem } from "../../tipos/operacao";
import { MOTIVO_INTERVENCAO, SITUACAO } from "../operacao/textos";
import { EventosPesagem } from "./EventosPesagem";
import { CLASSIFICACAO, formaSituacao, formatarDataHora, traduzir } from "./textos";

const VAZIOS = {
  data_inicio: "",
  data_fim: "",
  aberta: "",
  situacao: "",
  tipo_operacao: "",
  classificacao: "",
  liberacao_manual: "",
  placa: "",
  agendamento_id: "",
};
type Filtros = typeof VAZIOS;

const peso = (v: string | null) => (v === null ? "—" : formatarPeso(v));

function Situacao({ p }: { p: Pesagem }) {
  return (
    <div className="flex flex-col gap-1">
      <IndicadorEstado tipo={formaSituacao(p.situacao)} texto={traduzir(SITUACAO, p.situacao)} />
      {p.situacao === "AGUARDANDO_INTERVENCAO" && p.motivo_intervencao && (
        <span className="text-sm">{traduzir(MOTIVO_INTERVENCAO, p.motivo_intervencao)}</span>
      )}
    </div>
  );
}

/** Campos de `422` que a tela sabe explicar (spec 021 §7). */
function detalheFiltro(erro: unknown): string | null {
  if (!(erro instanceof ErroRequisicao) || erro.status !== 422) return null;
  const codigos = erro.erro?.campos.map((c) => c.codigo) ?? [];
  return codigos.includes("PLACA_INVALIDA") ? textoCodigo("PLACA_INVALIDA") : null;
}

export function PaginaHistorico() {
  const [rascunho, setRascunho] = useState<Filtros>(VAZIOS);
  const [filtros, setFiltros] = useState<Filtros>(VAZIOS);
  const [pagina, setPagina] = useState(1);
  const [aberta, setAberta] = useState<Pesagem | null>(null);

  const lista = useCarga(
    async () => {
      // Filtro vazio não vai na consulta; os valores vêm de listas fechadas ou de campos tipados.
      const consulta: Record<string, string | number> = { pagina };
      for (const [nome, valor] of Object.entries(filtros)) if (valor) consulta[nome] = valor;
      return { dados: await listarPesagens(consulta), em: new Date() };
    },
    JSON.stringify([filtros, pagina]),
  );
  const dados = lista.dados?.dados;
  const paginas = dados ? Math.max(1, Math.ceil(dados.total / dados.tamanho_pagina)) : 1;

  const filtrar = (e: SubmitEvent) => {
    e.preventDefault();
    setFiltros({ ...rascunho, placa: rascunho.placa.trim() });
    setPagina(1);
  };
  const campo = (nome: keyof Filtros) => ({
    value: rascunho[nome],
    onChange: (e: { target: { value: string } }) => {
      setRascunho((r) => ({ ...r, [nome]: e.target.value }));
    },
  });
  const rotulo = "text-sm font-semibold";

  return (
    <section>
      <h1 className="mb-1 text-2xl font-bold">Histórico</h1>
      <p className="mb-4 text-suave">
        {lista.dados
          ? `Consulta feita às ${lista.dados.em.toLocaleTimeString("pt-BR")}. Esta tela não atualiza sozinha.`
          : "Esta tela não atualiza sozinha."}
      </p>
      <form onSubmit={filtrar} className="mb-4 flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Data inicial</span>
          <input type="date" className={CLASSE_ENTRADA} {...campo("data_inicio")} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Data final</span>
          <input type="date" className={CLASSE_ENTRADA} {...campo("data_fim")} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Pesagens</span>
          <select className={CLASSE_ENTRADA} {...campo("aberta")}>
            <option value="">Todas</option>
            <option value="true">Abertas</option>
            <option value="false">Encerradas</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Situação</span>
          <select className={CLASSE_ENTRADA} {...campo("situacao")}>
            <option value="">Todas</option>
            {Object.entries(SITUACAO).map(([codigo, texto]) => (
              <option key={codigo} value={codigo}>
                {texto}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Tipo</span>
          <select className={CLASSE_ENTRADA} {...campo("tipo_operacao")}>
            <option value="">Todos</option>
            <option value="CARGA">Carga</option>
            <option value="DESCARGA">Descarga</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Classificação</span>
          <select className={CLASSE_ENTRADA} {...campo("classificacao")}>
            <option value="">Todas</option>
            {Object.entries(CLASSIFICACAO).map(([codigo, texto]) => (
              <option key={codigo} value={codigo}>
                {texto}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Liberação manual</span>
          <select className={CLASSE_ENTRADA} {...campo("liberacao_manual")}>
            <option value="">Todas</option>
            <option value="true">Sim</option>
            <option value="false">Não</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Placa</span>
          <input className={`${CLASSE_ENTRADA} font-mono`} {...campo("placa")} />
        </label>
        <label className="flex flex-col gap-1">
          <span className={rotulo}>Nº do agendamento</span>
          <input type="number" min={1} className={CLASSE_ENTRADA} {...campo("agendamento_id")} />
        </label>
        <Botao type="submit" variante="acao">
          Filtrar
        </Botao>
        <Botao onClick={lista.recarregar}>Atualizar</Botao>
      </form>

      {aberta && (
        <EventosPesagem
          key={aberta.id}
          pesagem={aberta}
          aoFechar={() => {
            setAberta(null);
          }}
        />
      )}

      {lista.erro !== undefined ? (
        <div className="flex flex-col gap-2">
          <MensagemErro erro={lista.erro} aoTentarNovamente={lista.recarregar} />
          {detalheFiltro(lista.erro) && (
            <p className="font-semibold">{detalheFiltro(lista.erro)}</p>
          )}
        </div>
      ) : !dados ? (
        <p className="text-suave">Carregando…</p>
      ) : dados.itens.length === 0 ? (
        <p className="text-suave">Nenhuma pesagem encontrada.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-tinta">
                  {[
                    "Criada em",
                    "Placa",
                    "Tipo",
                    "Motorista",
                    "Produto",
                    "Situação",
                    "Peso inicial",
                    "Peso final",
                    "Peso líquido",
                    "Liberação manual",
                    "Eventos",
                  ].map((c) => (
                    <th key={c} scope="col" className="px-3 py-2 text-sm font-semibold">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dados.itens.map((p) => (
                  <tr key={p.id} className="border-b border-fio align-top">
                    <td className="px-3 py-2">{formatarDataHora(p.criado_em)}</td>
                    <td className="px-3 py-2 font-mono">{p.placa}</td>
                    <td className="px-3 py-2">
                      {p.tipo_operacao === "CARGA" ? "Carga" : "Descarga"}
                    </td>
                    <td className="px-3 py-2">{p.motorista_nome}</td>
                    <td className="px-3 py-2">{p.produto_descricao}</td>
                    <td className="px-3 py-2">
                      <Situacao p={p} />
                    </td>
                    <td className="px-3 py-2">{peso(p.peso_inicial_kg)}</td>
                    <td className="px-3 py-2">{peso(p.peso_final_kg)}</td>
                    <td className="px-3 py-2">
                      {peso(p.peso_liquido_kg)}
                      {p.classificacao && (
                        <span className="block text-sm text-suave">
                          {traduzir(CLASSIFICACAO, p.classificacao)}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2">{p.liberacao_manual ? "Sim" : "Não"}</td>
                    <td className="px-3 py-2">
                      <Botao
                        aria-label={`Eventos da pesagem de ${p.placa} nº ${String(p.id)}`}
                        onClick={() => {
                          setAberta(p);
                        }}
                      >
                        Eventos
                      </Botao>
                    </td>
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
              Página {pagina} de {paginas} · {dados.total}{" "}
              {dados.total === 1 ? "pesagem" : "pesagens"}
            </span>
          </nav>
        </>
      )}
    </section>
  );
}
