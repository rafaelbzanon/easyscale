import { useState } from "react";
import { listarEventosPesagem } from "../../api/historico";
import { Botao } from "../../componentes/Botao";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { MensagemErro } from "../../componentes/MensagemErro";
import { useCarga } from "../../componentes/useCarga";
import { formatarPeso } from "../../componentes/formatar-peso";
import type { EventoPesagem } from "../../tipos/historico";
import type { Pesagem } from "../../tipos/operacao";
import { MOTIVO_INTERVENCAO, SITUACAO } from "../operacao/textos";
import { CLASSIFICACAO, formatarDataHora, nomeEvento, TIPO_EVENTO, traduzir } from "./textos";

const situacao = (s: string | null) => (s ? traduzir(SITUACAO, s) : "—");

function Resultado({ e }: { e: EventoPesagem }) {
  const tentativas = `${String(e.tentativas ?? 0)} tentativa${e.tentativas === 1 ? "" : "s"}`;
  if (e.resultado === "CONFIRMADO")
    return <IndicadorEstado tipo="ok" texto={`confirmado (${tentativas})`} />;
  if (e.resultado === "FALHA")
    return <IndicadorEstado tipo="falha" texto={`FALHA (${tentativas})`} />;
  // SEM_CONFIRMACAO nunca é sucesso: o estado da cancela é desconhecido (spec 004).
  return <IndicadorEstado tipo="falha" texto={`SEM CONFIRMAÇÃO (${tentativas})`} />;
}

function OQueAconteceu({ e }: { e: EventoPesagem }) {
  return (
    <div className="flex flex-col gap-1">
      {e.tipo === "COMANDO_CANCELA" ? (
        <p>
          Cancela de {e.cancela === "ENTRADA" ? "entrada" : e.cancela === "SAIDA" ? "saída" : "—"}:{" "}
          {e.comando === "ABRIR" ? "abrir" : e.comando === "FECHAR" ? "fechar" : "—"} ·{" "}
          <Resultado e={e} />
        </p>
      ) : (
        <p>
          <span className="font-semibold">{nomeEvento(e.evento)}</span>
        </p>
      )}
      {e.tipo === "TRANSICAO" && (
        <p>
          {situacao(e.situacao_origem)} → {situacao(e.situacao_destino)}
        </p>
      )}
      {e.tipo === "TRANSICAO_REJEITADA" && (
        <p>
          Rejeitada: nada mudou. Situação: {situacao(e.situacao_origem)}.
          {e.motivo_rejeicao && ` Motivo: ${e.motivo_rejeicao}.`}
        </p>
      )}
      {e.tipo === "EVENTO_REGISTRADO" && <p>Situação: {situacao(e.situacao_origem)}.</p>}
      {e.motivo_intervencao && (
        <p>Intervenção: {traduzir(MOTIVO_INTERVENCAO, e.motivo_intervencao)}.</p>
      )}
      {e.motivo_dispositivo && <p>Motivo do dispositivo: {e.motivo_dispositivo}.</p>}
      {e.peso_kg && (
        <p>
          Peso: {formatarPeso(e.peso_kg)}
          {e.peso_liquido_kg && ` · líquido ${formatarPeso(e.peso_liquido_kg)}`}
          {e.classificacao && ` (${traduzir(CLASSIFICACAO, e.classificacao)})`}
        </p>
      )}
      {(e.imagem_id !== null || e.leitura_placa_id !== null) && (
        <p className="text-sm text-suave">
          {e.imagem_id !== null && `Imagem da decisão nº ${String(e.imagem_id)}. `}
          {e.leitura_placa_id !== null && `Leitura de placa nº ${String(e.leitura_placa_id)}.`}
        </p>
      )}
    </div>
  );
}

/** Eventos de uma pesagem, do mais antigo ao mais recente (spec 021 §6.2). */
export function EventosPesagem({ pesagem, aoFechar }: { pesagem: Pesagem; aoFechar: () => void }) {
  const [pagina, setPagina] = useState(1);
  const eventos = useCarga(
    () => listarEventosPesagem(pesagem.id, { pagina }),
    `${String(pesagem.id)}/${String(pagina)}`,
  );
  const lista = eventos.dados;
  const paginas = lista ? Math.max(1, Math.ceil(lista.total / lista.tamanho_pagina)) : 1;

  return (
    <section aria-label="Eventos da pesagem" className="mb-6 border border-fio p-4">
      <div className="mb-3 flex flex-wrap items-center gap-4">
        <h2 className="text-lg font-bold">
          Eventos · <span className="font-mono">{pesagem.placa}</span> · pesagem nº {pesagem.id}
        </h2>
        <Botao className="ml-auto" onClick={aoFechar}>
          Fechar
        </Botao>
      </div>
      {eventos.erro !== undefined ? (
        <MensagemErro erro={eventos.erro} aoTentarNovamente={eventos.recarregar} />
      ) : !lista ? (
        <p className="text-suave">Carregando…</p>
      ) : lista.itens.length === 0 ? (
        <p className="text-suave">Nenhum evento registrado.</p>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-tinta">
                  {["Quando", "Tipo", "O que aconteceu", "Quem e por quê"].map((c) => (
                    <th key={c} scope="col" className="px-3 py-2 text-sm font-semibold">
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lista.itens.map((e) => (
                  <tr key={e.id} className="border-b border-fio align-top">
                    <td className="px-3 py-2">{formatarDataHora(e.ocorrido_em)}</td>
                    <td className="px-3 py-2">{traduzir(TIPO_EVENTO, e.tipo)}</td>
                    <td className="px-3 py-2">
                      <OQueAconteceu e={e} />
                    </td>
                    <td className="px-3 py-2">
                      {e.responsavel ? (
                        <>
                          <p className="font-semibold">{e.responsavel.nome}</p>
                          {e.motivo && <p>Motivo: {e.motivo}</p>}
                        </>
                      ) : (
                        "Automático"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <nav
            aria-label="Paginação dos eventos"
            className="mt-4 flex flex-wrap items-center gap-3"
          >
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
              Página {pagina} de {paginas} · {lista.total}{" "}
              {lista.total === 1 ? "evento" : "eventos"}
            </span>
          </nav>
        </>
      )}
    </section>
  );
}
