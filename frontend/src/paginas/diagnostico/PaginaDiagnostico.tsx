import { useEffect, useState, type ReactNode, type SyntheticEvent } from "react";
import { ErroRequisicao } from "../../api/cliente-api";
import {
  excluirImagemDecisao,
  listarLeiturasPlaca,
  obterConteudoImagemDecisao,
  obterDispositivos,
  obterImagemAtual,
  obterImagemDecisao,
  obterLeituraPlaca,
  obterSimuladores,
  simularChegada,
  trocarCenarioBalanca,
  trocarCenarioCancela,
  trocarCenarioPosicao,
} from "../../api/diagnostico";
import { Botao } from "../../componentes/Botao";
import { Campo, CLASSE_ENTRADA } from "../../componentes/Campo";
import { formatarHora, formatarIdade } from "../../componentes/formatar-peso";
import { ImagemComRois } from "../../componentes/ImagemComRois";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { MensagemErro } from "../../componentes/MensagemErro";
import { useSessao } from "../../componentes/useSessao";
import type { Lista } from "../../tipos/comum";
import type {
  CameraDiagnostico,
  CenariosSimuladores,
  ImagemDecisao,
  LeituraPlacaDetalhe,
} from "../../tipos/diagnostico";
import type { EstadoOperacao, LeituraPlaca } from "../../tipos/operacao";
import {
  indicadorIdentificacao,
  indicadorPosicao,
  MOTIVO_NAO_AUTORIZACAO,
} from "../operacao/textos";
import { useCanalOperacao } from "../operacao/useCanalOperacao";

const codigoErro = (e: unknown) =>
  e instanceof ErroRequisicao ? (e.erro?.campos[0]?.codigo ?? e.erro?.codigo ?? null) : null;

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section aria-label={titulo} className="flex flex-col gap-3 border-t border-fio pt-4">
      <h2 className="text-xl font-bold">{titulo}</h2>
      {children}
    </section>
  );
}

/** Spec 023. Cada seção depende de uma permissão; o backend decide (403). */
export function PaginaDiagnostico() {
  const { permissoes } = useSessao();
  const pode = (p: string) => permissoes.includes(p);
  const canal = useCanalOperacao();
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold">Diagnóstico</h1>
        {canal.desatualizada ? (
          <IndicadorEstado tipo="atencao" texto="Tela desatualizada" />
        ) : (
          <IndicadorEstado tipo="ok" texto="Atualizada" />
        )}
      </div>
      {pode("CONSULTAR_IMAGENS_TEMPO_REAL") && (
        <Cameras estado={canal.estado} ativa={!canal.desatualizada} agora={canal.agora} />
      )}
      <Reconhecimentos
        podeDetalhar={pode("CONSULTAR_IMAGENS_DECISAO")}
        podeExcluir={pode("EXCLUIR_IMAGENS_DECISAO")}
      />
      {pode("CONTROLAR_SIMULADORES") && <Simuladores />}
    </div>
  );
}

function Cameras({
  estado,
  ativa,
  agora,
}: {
  estado: EstadoOperacao | null;
  ativa: boolean;
  agora: number;
}) {
  const [intervalo, setIntervalo] = useState<number | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  useEffect(() => {
    let vivo = true;
    obterDispositivos().then(
      (d) => {
        if (vivo) setIntervalo(d.intervalo_imagem_ms);
      },
      (e: unknown) => {
        if (vivo) setErro(e);
      },
    );
    return () => {
      vivo = false;
    };
  }, []);
  return (
    <Secao titulo="Câmeras">
      {erro !== null && <MensagemErro erro={erro} />}
      {intervalo !== null && (
        <div className="grid gap-6 lg:grid-cols-2">
          {(["identificacao", "posicao"] as const).map((camera) => (
            <ImagemCamera
              key={camera}
              camera={camera}
              intervaloMs={intervalo}
              ativa={ativa}
              agora={agora}
              resultado={
                estado
                  ? camera === "identificacao"
                    ? indicadorIdentificacao(estado.dispositivos.identificacao)
                    : indicadorPosicao(estado.dispositivos.posicao)
                  : null
              }
            />
          ))}
        </div>
      )}
    </Secao>
  );
}

function ImagemCamera({
  camera,
  intervaloMs,
  ativa,
  agora,
  resultado,
}: {
  camera: CameraDiagnostico;
  intervaloMs: number;
  ativa: boolean;
  agora: number;
  resultado: ReturnType<typeof indicadorPosicao> | null;
}) {
  const [imagem, setImagem] = useState<{ imagem: Blob; capturadaEm: string | null } | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  useEffect(() => {
    // Só pede com a tela atualizada e visível (011 §6.3).
    if (!ativa) return;
    let vivo = true;
    const buscar = () => {
      if (document.visibilityState !== "visible") return;
      obterImagemAtual(camera).then(
        (i) => {
          if (vivo) {
            setImagem(i);
            setErro(null);
          }
        },
        (e: unknown) => {
          if (vivo) {
            setImagem(null);
            setErro(e);
          }
        },
      );
    };
    buscar();
    const t = setInterval(buscar, intervaloMs);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, [camera, intervaloMs, ativa]);

  const nome = camera === "identificacao" ? "Câmera de identificação" : "Câmera de posição";
  return (
    <figure className="flex flex-col gap-2">
      <figcaption className="flex flex-wrap items-center gap-3">
        <span className="font-semibold">{nome}</span>
        {resultado && <IndicadorEstado {...resultado} />}
      </figcaption>
      {codigoErro(erro) === "SEM_IMAGEM" ? (
        <p className="border border-fio p-6 text-suave">Sem imagem desta câmera.</p>
      ) : erro !== null ? (
        <MensagemErro erro={erro} />
      ) : imagem ? (
        <div className={ativa ? undefined : "opacity-55"}>
          <ImagemComRois imagem={imagem.imagem} descricao={`Imagem atual: ${nome}`} />
          <p className="text-sm text-suave">
            {!ativa
              ? "Imagem parada: tela desatualizada."
              : imagem.capturadaEm
                ? `Capturada ${formatarIdade(new Date(imagem.capturadaEm).toISOString(), agora)}`
                : null}
          </p>
        </div>
      ) : (
        <p className="text-suave">Carregando…</p>
      )}
    </figure>
  );
}

function Reconhecimentos({
  podeDetalhar,
  podeExcluir,
}: {
  podeDetalhar: boolean;
  podeExcluir: boolean;
}) {
  const [pagina, setPagina] = useState(1);
  const [soNaoAutorizadas, setSoNaoAutorizadas] = useState(false);
  const [lista, setLista] = useState<Lista<LeituraPlaca> | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [aberta, setAberta] = useState<number | null>(null);
  useEffect(() => {
    let vivo = true;
    listarLeiturasPlaca({
      pagina,
      ...(soNaoAutorizadas ? { decisao: "NAO_AUTORIZADA" as const } : {}),
    }).then(
      (l) => {
        if (vivo) {
          setLista(l);
          setErro(null);
        }
      },
      (e: unknown) => {
        if (vivo) setErro(e);
      },
    );
    return () => {
      vivo = false;
    };
  }, [pagina, soNaoAutorizadas]);

  const paginas = lista ? Math.max(1, Math.ceil(lista.total / lista.tamanho_pagina)) : 1;
  return (
    <Secao titulo="Reconhecimentos">
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={soNaoAutorizadas}
          onChange={(e) => {
            setSoNaoAutorizadas(e.target.checked);
            setPagina(1);
          }}
        />
        Só não autorizadas
      </label>
      {erro !== null && <MensagemErro erro={erro} />}
      {lista && lista.itens.length === 0 && <p className="text-suave">Nenhuma leitura.</p>}
      {lista && lista.itens.length > 0 && (
        <ul className="flex flex-col">
          {lista.itens.map((l) => (
            <li key={l.id} className="flex flex-col gap-3 border-b border-fio py-3">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
                <span className="text-sm text-suave">{formatarHora(l.decidida_em)}</span>
                <span className="font-mono text-lg font-bold">
                  {l.placa_normalizada ?? "Sem placa"}
                </span>
                {l.decisao === "NAO_AUTORIZADA" ? (
                  <IndicadorEstado
                    tipo="falha"
                    texto={`Não autorizada${l.motivo ? `: ${MOTIVO_NAO_AUTORIZACAO[l.motivo]}` : ""}`}
                  />
                ) : (
                  <IndicadorEstado
                    tipo="ok"
                    texto={l.decisao === "AUTORIZADA" ? "Autorizada" : "Retorno aceito"}
                  />
                )}
                {l.confianca !== null && <span className="text-sm">Confiança {l.confianca}</span>}
                {podeDetalhar && (
                  <Botao
                    aria-expanded={aberta === l.id}
                    onClick={() => {
                      setAberta(aberta === l.id ? null : l.id);
                    }}
                  >
                    {aberta === l.id ? "Fechar detalhes" : "Ver detalhes"}
                  </Botao>
                )}
              </div>
              {aberta === l.id && <DetalheLeitura id={l.id} podeExcluir={podeExcluir} />}
            </li>
          ))}
        </ul>
      )}
      {paginas > 1 && (
        <div className="flex items-center gap-3 text-sm">
          <Botao
            disabled={pagina <= 1}
            onClick={() => {
              setPagina(pagina - 1);
            }}
          >
            Anterior
          </Botao>
          <span>
            Página {pagina} de {paginas}
          </span>
          <Botao
            disabled={pagina >= paginas}
            onClick={() => {
              setPagina(pagina + 1);
            }}
          >
            Próxima
          </Botao>
        </div>
      )}
    </Secao>
  );
}

function DetalheLeitura({ id, podeExcluir }: { id: number; podeExcluir: boolean }) {
  const [leitura, setLeitura] = useState<LeituraPlacaDetalhe | null>(null);
  const [dadosImagem, setDadosImagem] = useState<ImagemDecisao | null>(null);
  const [conteudo, setConteudo] = useState<Blob | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [recarga, setRecarga] = useState(0);
  useEffect(() => {
    // Lido por função: o TypeScript não estreita o valor entre os awaits.
    const controle = { vivo: true };
    const ativo = () => controle.vivo;
    obterLeituraPlaca(id)
      .then(async (l) => {
        if (!ativo()) return;
        setLeitura(l);
        if (l.imagem_id === null) return;
        const img = await obterImagemDecisao(l.imagem_id);
        if (!ativo()) return;
        setDadosImagem(img);
        setConteudo(img.excluida ? null : (await obterConteudoImagemDecisao(l.imagem_id)).imagem);
      })
      .catch((e: unknown) => {
        if (ativo()) setErro(e);
      });
    return () => {
      controle.vivo = false;
    };
  }, [id, recarga]);

  if (erro !== null && codigoErro(erro) !== "IMAGEM_EXCLUIDA") return <MensagemErro erro={erro} />;
  if (!leitura) return <p className="text-suave">Carregando…</p>;
  const rois = leitura.leituras.map((x) => x.roi);
  return (
    <div className="grid gap-6 bg-claro p-4 lg:grid-cols-2">
      <div className="flex flex-col gap-2">
        {dadosImagem?.excluida ? (
          <p className="border border-fio p-4">
            Imagem excluída por {dadosImagem.excluida_por_nome ?? "?"} em{" "}
            {dadosImagem.excluida_em
              ? new Date(dadosImagem.excluida_em).toLocaleString("pt-BR")
              : "?"}
            . Motivo: {dadosImagem.motivo_exclusao ?? "?"}.
          </p>
        ) : conteudo ? (
          <ImagemComRois
            imagem={conteudo}
            rois={rois}
            descricao={`Imagem da leitura ${String(id)}`}
          />
        ) : leitura.imagem_id === null ? (
          <p className="text-suave">Sem imagem salva.</p>
        ) : (
          <p className="text-suave">Carregando a imagem…</p>
        )}
        {podeExcluir && dadosImagem && !dadosImagem.excluida && (
          <ExcluirImagem
            imagemId={dadosImagem.id}
            aoExcluir={() => {
              setConteudo(null);
              setRecarga((r) => r + 1);
            }}
          />
        )}
      </div>
      <dl className="grid grid-cols-[auto_1fr] content-start gap-x-4 gap-y-1 text-sm">
        <dt className="text-suave">Texto bruto</dt>
        <dd className="font-mono">{leitura.placa_lida ?? "—"}</dd>
        <dt className="text-suave">Placa normalizada</dt>
        <dd className="font-mono">{leitura.placa_normalizada ?? "—"}</dd>
        <dt className="text-suave">Formato</dt>
        <dd>
          {leitura.formato === "MERCOSUL"
            ? "Mercosul"
            : leitura.formato === "ANTIGO"
              ? "Antigo"
              : "—"}
        </dd>
        <dt className="text-suave">Correções de OCR</dt>
        <dd>
          {leitura.correcoes.length === 0
            ? "Nenhuma"
            : leitura.correcoes
                .map((c) => `posição ${String(c.posicao)}: ${c.lido} → ${c.corrigido}`)
                .join("; ")}
        </dd>
        <dt className="text-suave">Confiança</dt>
        <dd>{leitura.confianca ?? "—"}</dd>
        <dt className="text-suave">Origem</dt>
        <dd>{leitura.origem}</dd>
        <dt className="col-span-2 mt-2 font-semibold">Leituras por ROI</dt>
        {leitura.leituras.length === 0 ? (
          <dd className="col-span-2 text-suave">Nenhuma ROI encontrada.</dd>
        ) : (
          <dd className="col-span-2">
            <ol className="flex flex-col gap-1">
              {leitura.leituras.map((x, i) => (
                <li key={i}>
                  <span className="font-semibold">ROI {i + 1}</span>{" "}
                  <span className="text-suave">
                    ({x.roi.x}, {x.roi.y}, {x.roi.largura}×{x.roi.altura})
                  </span>
                  :{" "}
                  {x.textos.length === 0
                    ? "nenhum texto"
                    : x.textos.map((t) => `${t.texto} (${t.confianca})`).join(", ")}
                </li>
              ))}
            </ol>
          </dd>
        )}
      </dl>
    </div>
  );
}

function ExcluirImagem({ imagemId, aoExcluir }: { imagemId: number; aoExcluir: () => void }) {
  const [aberta, setAberta] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);
  const confirmar = (e: SyntheticEvent) => {
    e.preventDefault();
    setEnviando(true);
    excluirImagemDecisao(imagemId, { motivo: motivo.trim() }).then(
      () => {
        setEnviando(false);
        setAberta(false);
        aoExcluir();
      },
      (x: unknown) => {
        setEnviando(false);
        setErro(x);
      },
    );
  };
  if (!aberta)
    return (
      <Botao
        className="self-start"
        onClick={() => {
          setAberta(true);
        }}
      >
        Excluir imagem
      </Botao>
    );
  return (
    <form onSubmit={confirmar} className="flex flex-col gap-2 border border-fio p-3">
      <p className="text-sm">
        Apaga só os bytes da imagem. A leitura e a operação continuam registradas.
      </p>
      <Campo
        rotulo="Motivo da exclusão"
        required
        maxLength={200}
        value={motivo}
        onChange={(e) => {
          setMotivo(e.target.value);
        }}
      />
      {erro !== null && <MensagemErro erro={erro} />}
      <div className="flex gap-2">
        <Botao type="submit" variante="acao" disabled={enviando || motivo.trim() === ""}>
          Confirmar exclusão
        </Botao>
        <Botao
          onClick={() => {
            setAberta(false);
          }}
        >
          Cancelar
        </Botao>
      </div>
    </form>
  );
}

type CenarioBalanca = CenariosSimuladores["balanca"]["cenario"];
type CenarioCancela = CenariosSimuladores["cancelas"][number]["cenario"];
type CenarioPosicao = CenariosSimuladores["posicao"]["cenario"];
const CENARIOS_BALANCA: Record<CenarioBalanca, string> = {
  ESTAVEL: "Estável",
  INSTAVEL: "Instável",
  SEM_RESPOSTA: "Sem resposta",
  SEM_RESPOSTA_NA_PRIMEIRA: "Sem resposta na primeira leitura",
  QUADRO_CORROMPIDO: "Quadro corrompido",
  DESCONECTADA: "Desconectada",
};
const COM_PESO: CenarioBalanca[] = ["ESTAVEL", "INSTAVEL", "SEM_RESPOSTA_NA_PRIMEIRA"];
const CENARIOS_CANCELA: Record<CenarioCancela, string> = {
  CONFIRMADO: "Confirma o comando",
  CONFIRMADO_NA_SEGUNDA: "Confirma na segunda tentativa",
  NAO_MOVE: "Não se move",
  FALHA: "Falha",
  SENSOR_SEM_RESPOSTA: "Sensor sem resposta",
};
const CENARIOS_POSICAO: Record<CenarioPosicao, string> = {
  CONFIRMADA: "Caminhão em posição",
  AUSENTE: "Balança vazia",
  INCONCLUSIVA: "Inconclusiva",
};

function Seletor<T extends string>({
  rotulo,
  valor,
  opcoes,
  aoMudar,
}: {
  rotulo: string;
  valor: T;
  opcoes: Record<T, string>;
  aoMudar: (v: T) => void;
}) {
  const id = `seletor-${rotulo.replace(/\W+/g, "-")}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-sm font-semibold">
        {rotulo}
      </label>
      <select
        id={id}
        value={valor}
        className={CLASSE_ENTRADA}
        onChange={(e) => {
          aoMudar(e.target.value as T);
        }}
      >
        {(Object.keys(opcoes) as T[]).map((k) => (
          <option key={k} value={k}>
            {opcoes[k]}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Só aparece quando o backend oferece (todos os dispositivos em SIMULADO, 011 §6.4). */
function Simuladores() {
  const [cenarios, setCenarios] = useState<CenariosSimuladores | null>(null);
  const [indisponivel, setIndisponivel] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const [balanca, setBalanca] = useState<{
    cenario: CenarioBalanca;
    peso: string;
    amplitude: string;
  }>({
    cenario: "ESTAVEL",
    peso: "",
    amplitude: "",
  });
  const [placa, setPlaca] = useState("");
  const [confianca, setConfianca] = useState("");

  const tratar = (pedido: Promise<CenariosSimuladores>) => {
    setErro(null);
    pedido.then(setCenarios, (e: unknown) => {
      if (e instanceof ErroRequisicao && (e.status === 404 || e.status === 403))
        setIndisponivel(true);
      else setErro(e);
    });
  };
  useEffect(() => {
    let vivo = true;
    obterSimuladores().then(
      (c) => {
        if (vivo) {
          setCenarios(c);
          setBalanca({
            cenario: c.balanca.cenario,
            peso: c.balanca.peso_kg ?? "",
            amplitude: c.balanca.amplitude_kg ?? "",
          });
        }
      },
      () => {
        // 404 (equipamento real) ou 403: a seção não aparece (spec 023 §3.4).
        if (vivo) setIndisponivel(true);
      },
    );
    return () => {
      vivo = false;
    };
  }, []);

  if (indisponivel && cenarios) return <p className="text-suave">Simuladores indisponíveis.</p>;
  if (indisponivel || !cenarios) return null;
  const comPeso = COM_PESO.includes(balanca.cenario);
  const instavel = balanca.cenario === "INSTAVEL";
  return (
    <Secao titulo="Simuladores">
      <p className="text-sm">
        Trocar o cenário não aciona nada; vale a partir da próxima leitura ou comando.
      </p>
      {erro !== null && <MensagemErro erro={erro} />}
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          tratar(
            trocarCenarioBalanca({
              cenario: balanca.cenario,
              peso_kg: comPeso ? balanca.peso : null,
              amplitude_kg: instavel ? balanca.amplitude : null,
            }),
          );
        }}
      >
        <Seletor
          rotulo="Balança"
          valor={balanca.cenario}
          opcoes={CENARIOS_BALANCA}
          aoMudar={(cenario) => {
            setBalanca({ ...balanca, cenario });
          }}
        />
        {comPeso && (
          <Campo
            rotulo="Peso (kg)"
            required
            inputMode="decimal"
            value={balanca.peso}
            onChange={(e) => {
              setBalanca({ ...balanca, peso: e.target.value });
            }}
          />
        )}
        {instavel && (
          <Campo
            rotulo="Amplitude (kg)"
            required
            inputMode="decimal"
            value={balanca.amplitude}
            onChange={(e) => {
              setBalanca({ ...balanca, amplitude: e.target.value });
            }}
          />
        )}
        <Botao type="submit" variante="acao">
          Aplicar à balança
        </Botao>
      </form>
      <div className="flex flex-wrap gap-3">
        {cenarios.cancelas.map((c) => (
          <Seletor
            key={c.cancela}
            rotulo={c.cancela === "ENTRADA" ? "Cancela de entrada" : "Cancela de saída"}
            valor={c.cenario}
            opcoes={CENARIOS_CANCELA}
            aoMudar={(cenario) => {
              tratar(
                trocarCenarioCancela(c.cancela === "ENTRADA" ? "entrada" : "saida", { cenario }),
              );
            }}
          />
        ))}
        <Seletor
          rotulo="Posição do caminhão"
          valor={cenarios.posicao.cenario}
          opcoes={CENARIOS_POSICAO}
          aoMudar={(cenario) => {
            tratar(trocarCenarioPosicao({ cenario }));
          }}
        />
      </div>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          tratar(
            simularChegada({ textos: placa.trim() ? [{ texto: placa.trim(), confianca }] : [] }),
          );
        }}
      >
        <Campo
          rotulo="Placa da chegada"
          value={placa}
          onChange={(e) => {
            setPlaca(e.target.value);
          }}
        />
        <Campo
          rotulo="Confiança (0 a 1)"
          required={placa.trim() !== ""}
          inputMode="decimal"
          value={confianca}
          onChange={(e) => {
            setConfianca(e.target.value);
          }}
        />
        <Botao type="submit" variante="acao">
          Simular chegada
        </Botao>
        <span className="text-sm text-suave">Na fila: {cenarios.chegadas_na_fila}</span>
      </form>
    </Secao>
  );
}
