import { useState, type ReactNode, type SyntheticEvent } from "react";
import { ErroRequisicao } from "../../api/cliente-api";
import { executarAcao, liberarCaminhao } from "../../api/operacao";
import { AreaAcoes } from "../../componentes/AreaAcoes";
import { Botao } from "../../componentes/Botao";
import { Campo } from "../../componentes/Campo";
import { formatarHora, formatarIdade, formatarPeso } from "../../componentes/formatar-peso";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { MensagemErro } from "../../componentes/MensagemErro";
import { useSessao } from "../../componentes/useSessao";
import type { AcaoManual, EstadoOperacao, LiberacaoCaminhao, Pesagem } from "../../tipos/operacao";
import {
  ACAO,
  ETAPA_LIBERACAO,
  FALHA_LIBERACAO,
  indicadorAvaliacao,
  indicadorCancela,
  indicadorComando,
  indicadorComunicacao,
  indicadorIdentificacao,
  indicadorPosicao,
  MOTIVO_INTERVENCAO,
  MOTIVO_NAO_AUTORIZACAO,
  SITUACAO,
  STATUS_AGENDAMENTO,
} from "./textos";
import { useCanalOperacao } from "./useCanalOperacao";

const MENSAGEM_CONFLITO: Record<string, string> = {
  VERSAO_DESATUALIZADA:
    "A pesagem mudou desde que você abriu a ação. Confira a situação e peça de novo.",
  TRANSICAO_REJEITADA: "Essa ação não vale mais na situação atual.",
  LIBERACAO_EM_CURSO: "Já existe uma liberação em curso para esse caminhão.",
  OPERACAO_NAO_OCUPA_BALANCA: "Esse caminhão não está mais aguardando liberação.",
};
const textoConflito = (erro: unknown) =>
  erro instanceof ErroRequisicao && erro.status === 409
    ? (erro.erro?.campos.map((c) => MENSAGEM_CONFLITO[c.codigo]).find(Boolean) ?? null)
    : null;

/** Spec 022. Quem decide é o backend; a tela só mostra e pede (S-5). */
export function PaginaOperacao() {
  const canal = useCanalOperacao();
  const { estado, desatualizada } = canal;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold">Operação</h1>
        {!canal.sincronizado && !canal.canalFechado ? (
          <IndicadorEstado tipo="atencao" texto="Sincronizando…" />
        ) : desatualizada ? (
          <IndicadorEstado tipo="atencao" texto="Tela desatualizada" />
        ) : (
          <IndicadorEstado tipo="ok" texto="Atualizada" />
        )}
        {canal.canalFechado && <Botao onClick={canal.reconectar}>Reconectar</Botao>}
      </div>
      {estado && (
        // Desatualizada: os dados ficam esmaecidos para não parecerem atuais (ADR-0005 §4.4).
        <div className={desatualizada ? "opacity-55" : undefined}>
          <Painel estado={estado} agora={canal.agora} />
        </div>
      )}
      <AreaAcoes bloqueada={desatualizada}>
        {estado ? (
          <div className="flex w-full flex-col gap-6">
            <Fila pesagens={estado.pesagens_abertas} aoResponder={canal.aplicarPesagem} />
            {estado.liberacoes_caminhao.length > 0 && (
              <Liberacoes liberacoes={estado.liberacoes_caminhao} estado={estado} />
            )}
          </div>
        ) : (
          <p className="text-suave">Carregando o estado da operação…</p>
        )}
      </AreaAcoes>
    </div>
  );
}

function Bloco({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section aria-label={titulo} className="flex flex-col gap-2 border-t border-fio pt-3">
      <h2 className="text-sm font-bold tracking-wide text-suave uppercase">{titulo}</h2>
      {children}
    </section>
  );
}

/** Balança, cancelas e última placa; também usado na FE-306. */
export function Painel({ estado, agora }: { estado: EstadoOperacao; agora: number }) {
  const { balanca, cancelas, posicao, identificacao } = estado.dispositivos;
  const avaliacao = indicadorAvaliacao(balanca);
  const leitura = estado.ultima_leitura_placa;
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Bloco titulo="Balança">
        {balanca.ultima_leitura ? (
          <p>
            <span className="text-3xl font-bold">
              {formatarPeso(balanca.ultima_leitura.peso_kg)}
            </span>
            <span className="block text-sm text-suave">
              Leitura, não é peso aceito · {formatarIdade(balanca.ultima_leitura.lida_em, agora)}
            </span>
          </p>
        ) : (
          <p className="text-suave">Nenhuma leitura recebida.</p>
        )}
        <IndicadorEstado {...indicadorComunicacao(balanca)} />
        {avaliacao && <IndicadorEstado {...avaliacao} />}
        <IndicadorEstado {...indicadorPosicao(posicao)} />
        <IndicadorEstado {...indicadorIdentificacao(identificacao)} />
      </Bloco>
      <Bloco titulo="Cancelas">
        {cancelas.map((c) => {
          const comando = indicadorComando(c);
          return (
            <div key={c.cancela} className="flex flex-col gap-1">
              <p className="flex flex-wrap items-center gap-2">
                <span className="w-16 font-semibold">
                  {c.cancela === "ENTRADA" ? "Entrada" : "Saída"}
                </span>
                <IndicadorEstado {...indicadorCancela(c)} />
              </p>
              {comando && (
                <p className="pl-18 text-sm">
                  <IndicadorEstado {...comando} />
                </p>
              )}
            </div>
          );
        })}
      </Bloco>
      <Bloco titulo="Última placa">
        {leitura ? (
          <>
            <p className="font-mono text-3xl font-bold">
              {leitura.placa_normalizada ?? "Sem placa"}
            </p>
            {leitura.decisao === "NAO_AUTORIZADA" ? (
              <IndicadorEstado
                tipo="falha"
                texto={`NÃO AUTORIZADA${leitura.motivo ? `: ${MOTIVO_NAO_AUTORIZACAO[leitura.motivo]}` : ""}`}
              />
            ) : (
              <IndicadorEstado
                tipo="ok"
                texto={leitura.decisao === "AUTORIZADA" ? "Autorizada" : "Retorno aceito"}
              />
            )}
            <p className="text-sm text-suave">
              {leitura.confianca !== null && `Confiança ${leitura.confianca} · `}
              {formatarHora(leitura.decidida_em)}
              {leitura.imagem_id !== null && " · imagem salva"}
            </p>
          </>
        ) : (
          <p className="text-suave">Nenhuma placa lida.</p>
        )}
      </Bloco>
    </div>
  );
}

export function Fila({
  pesagens,
  aoResponder,
}: {
  pesagens: Pesagem[];
  aoResponder: (p: Pesagem) => void;
}) {
  return (
    <Bloco
      titulo={`Fila · ${String(pesagens.length)} ${pesagens.length === 1 ? "pesagem aberta" : "pesagens abertas"}`}
    >
      {pesagens.length === 0 ? (
        <p className="text-suave">Nenhuma pesagem aberta.</p>
      ) : (
        <ul className="flex flex-col">
          {pesagens.map((p) => (
            <LinhaPesagem key={p.id} pesagem={p} aoResponder={aoResponder} />
          ))}
        </ul>
      )}
    </Bloco>
  );
}

function LinhaPesagem({
  pesagem: p,
  aoResponder,
}: {
  pesagem: Pesagem;
  aoResponder: (p: Pesagem) => void;
}) {
  const { permissoes } = useSessao();
  const acoes = p.acoes_disponiveis.filter((a) => permissoes.includes(ACAO[a].permissao));
  const intervencao = p.situacao === "AGUARDANDO_INTERVENCAO";
  const [aceito, setAceito] = useState(false);
  return (
    <li className="flex flex-col gap-2 border-b border-fio py-3">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <span className="font-mono text-xl font-bold">{p.placa}</span>
        <span>{p.tipo_operacao === "CARGA" ? "Carga" : "Descarga"}</span>
        {intervencao ? (
          <IndicadorEstado
            tipo="atencao"
            texto={`Aguardando intervenção${p.motivo_intervencao ? `: ${MOTIVO_INTERVENCAO[p.motivo_intervencao]}` : ""}`}
          />
        ) : (
          <span className="font-semibold">{SITUACAO[p.situacao]}</span>
        )}
        {intervencao && p.situacao_anterior && (
          <span className="text-sm text-suave">parou em: {SITUACAO[p.situacao_anterior]}</span>
        )}
      </div>
      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <Dado rotulo="Motorista" valor={p.motorista_nome} />
        <Dado rotulo="Produto" valor={p.produto_descricao} />
        <Dado rotulo="Agendamento" valor={STATUS_AGENDAMENTO[p.agendamento_status]} />
        <Dado
          rotulo="Peso inicial"
          valor={p.peso_inicial_kg ? formatarPeso(p.peso_inicial_kg) : "—"}
        />
        <Dado rotulo="Peso final" valor={p.peso_final_kg ? formatarPeso(p.peso_final_kg) : "—"} />
        <Dado rotulo="Líquido" valor={p.peso_liquido_kg ? formatarPeso(p.peso_liquido_kg) : "—"} />
        {p.comando_pendente && (
          <Dado
            rotulo="Comando em curso"
            valor={`${p.comando_pendente.comando === "ABRIR" ? "Abrir" : "Fechar"} ${p.comando_pendente.cancela === "ENTRADA" ? "entrada" : "saída"}`}
          />
        )}
      </dl>
      {acoes.length > 0 && (
        <AcoesComMotivo
          opcoes={acoes.map((a) => ({ id: a, ...ACAO[a] }))}
          enviar={(acao, motivo) =>
            executarAcao(p.id, acao as AcaoManual, { versao: p.versao, motivo }).then(aoResponder)
          }
          aoAceitar={() => {
            setAceito(true);
          }}
        />
      )}
      <AvisoPedido visivel={aceito} />
    </li>
  );
}

/** O 200 só diz que o pedido foi gravado; o efeito físico chega pelos eventos (009 §6.3). */
function AvisoPedido({ visivel }: { visivel: boolean }) {
  return visivel ? (
    <p role="status" className="text-sm font-semibold">
      Pedido aceito. O resultado chega pelos eventos.
    </p>
  ) : null;
}

function Dado({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex gap-1">
      <dt className="text-suave">{rotulo}:</dt>
      <dd>{valor}</dd>
    </div>
  );
}

export function Liberacoes({
  liberacoes,
  estado,
}: {
  liberacoes: LiberacaoCaminhao[];
  estado: EstadoOperacao;
}) {
  const { permissoes } = useSessao();
  const pode = permissoes.includes("LIBERAR_CAMINHAO_CANCELADO");
  const [aceitos, setAceitos] = useState<number[]>([]);
  return (
    <Bloco titulo="Caminhões cancelados na balança">
      <ul className="flex flex-col">
        {liberacoes.map((l) => {
          const livre = l.etapa === "PENDENTE" || l.etapa === "FALHOU";
          const placa = estado.pesagens_abertas.find((p) => p.id === l.pesagem_id)?.placa;
          return (
            <li key={l.pesagem_id} className="flex flex-col gap-2 border-b border-fio py-3">
              <p className="flex flex-wrap items-center gap-x-6 gap-y-1">
                <span className="font-semibold">
                  Pesagem {l.pesagem_id}
                  {placa ? ` · ${placa}` : ""}
                </span>
                <IndicadorEstado
                  tipo={l.etapa === "FALHOU" ? "falha" : "atencao"}
                  texto={`${ETAPA_LIBERACAO[l.etapa]}${l.motivo_falha ? `: ${FALHA_LIBERACAO[l.motivo_falha]}` : ""}`}
                />
                {l.pedido_por_nome && (
                  <span className="text-sm text-suave">pedido por {l.pedido_por_nome}</span>
                )}
              </p>
              {pode && livre && (
                <AcoesComMotivo
                  opcoes={[
                    {
                      id: "LIBERAR_CAMINHAO",
                      rotulo: "Liberar caminhão",
                      efeito: "Abre a saída e, com a balança vazia pelas câmeras, fecha de novo.",
                    },
                  ]}
                  enviar={(_, motivo) => liberarCaminhao(l.pesagem_id, { motivo })}
                  aoAceitar={() => {
                    setAceitos([...aceitos, l.pesagem_id]);
                  }}
                />
              )}
              <AvisoPedido visivel={aceitos.includes(l.pesagem_id)} />
            </li>
          );
        })}
      </ul>
    </Bloco>
  );
}

/** Botões de ação; cada um abre o motivo e a confirmação na linha (spec 022 §3.5). */
function AcoesComMotivo({
  opcoes,
  enviar,
  aoAceitar,
}: {
  opcoes: { id: string; rotulo: string; efeito: string }[];
  enviar: (id: string, motivo: string) => Promise<unknown>;
  aoAceitar: () => void;
}) {
  const [aberta, setAberta] = useState<string | null>(null);
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const opcao = opcoes.find((o) => o.id === aberta);

  const confirmar = (evento: SyntheticEvent) => {
    evento.preventDefault();
    if (!opcao) return;
    setEnviando(true);
    setErro(null);
    enviar(opcao.id, motivo.trim()).then(
      () => {
        setEnviando(false);
        setAberta(null);
        setMotivo("");
        aoAceitar();
      },
      (e: unknown) => {
        setEnviando(false);
        setErro(e);
      },
    );
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {opcoes.map((o) => (
          <Botao
            key={o.id}
            variante={aberta === o.id ? "neutro" : "acao"}
            aria-pressed={aberta === o.id}
            onClick={() => {
              setAberta(aberta === o.id ? null : o.id);
              setErro(null);
            }}
          >
            {o.rotulo}
          </Botao>
        ))}
      </div>
      {opcao && (
        <form
          onSubmit={confirmar}
          className="flex max-w-2xl flex-col gap-2 border border-fio bg-claro p-3"
        >
          <p className="text-sm">{opcao.efeito}</p>
          <Campo
            rotulo="Motivo"
            required
            maxLength={200}
            value={motivo}
            onChange={(e) => {
              setMotivo(e.target.value);
            }}
          />
          <Botao
            type="submit"
            variante="acao"
            disabled={enviando || motivo.trim() === ""}
            className="self-start"
          >
            Confirmar: {opcao.rotulo.toLowerCase()}
          </Botao>
        </form>
      )}
      {erro !== null && <MensagemErro erro={erro} texto={textoConflito(erro)} />}
    </div>
  );
}
