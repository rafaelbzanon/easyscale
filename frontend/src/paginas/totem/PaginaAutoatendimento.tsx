import { useEffect, useState, type ReactNode, type SubmitEvent } from "react";
import {
  disponibilidadeAutoatendimento,
  listarProdutosAutoatendimento,
  criarAgendamentoAutoatendimento,
} from "../../api/autoatendimento";
import { listarTodos } from "../../api/listar-todos";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { SimboloEstado } from "../../componentes/SimboloEstado";
import { useCarga } from "../../componentes/useCarga";
import type { TipoOperacao, VagaFaixa } from "../../tipos/agendamentos";
import type {
  AgendamentoAutoatendimento,
  ProdutoAutoatendimento,
} from "../../tipos/autoatendimento";
import { formatarData } from "../agendamentos/formatos";
import { proximosDias } from "./dias";
import { textoCarga, tratarErroEnvio, type Etapa } from "./erros";
import { TecladoTela } from "./TecladoTela";

// Escolhas da tela, não do contrato (spec 020 Q-F6): privacidade no totem público.
const INATIVIDADE_MS = 60_000;
const DIAS_A_FRENTE = 7;

interface Dados {
  tipo: TipoOperacao | null;
  produto: ProdutoAutoatendimento | null;
  data: string;
  faixa: VagaFaixa | null;
  placa: string;
  cpf: string;
  nota: string;
}
const VAZIO: Dados = {
  tipo: null,
  produto: null,
  data: "",
  faixa: null,
  placa: "",
  cpf: "",
  nota: "",
};

const filtroPlaca = (v: string) => v.toUpperCase();
const filtroCpf = (v: string) => v.replace(/\D/g, "").slice(0, 11);
const filtroNota = (v: string) => v.slice(0, 100);
const mascararCpf = (cpf: string) => `***.***.***-${cpf.slice(9)}`;

function Passo({
  titulo,
  indice,
  total,
  aoVoltar,
  children,
}: {
  titulo: string;
  indice: number;
  total: number;
  aoVoltar?: (() => void) | undefined;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-6">
      <div>
        <p className="text-suave">
          Passo {indice} de {total}
        </p>
        <h1 className="text-4xl font-bold">{titulo}</h1>
      </div>
      {children}
      {aoVoltar && (
        <div>
          <Botao onClick={aoVoltar}>Voltar</Botao>
        </div>
      )}
    </section>
  );
}

function Opcoes({
  carga,
  vazio,
  itens,
}: {
  carga: ReturnType<typeof useCarga<unknown>>;
  vazio: string;
  aoEscolher?: never;
  itens: ReactNode[];
}) {
  if (carga.erro !== undefined) {
    return (
      <div role="alert" className="flex flex-col gap-3 border border-vermelho bg-claro p-3">
        <p className="flex items-center gap-2 font-semibold text-vermelho">
          <SimboloEstado tipo="falha" />
          {textoCarga(carga.erro)}
        </p>
        <div>
          <Botao onClick={carga.recarregar}>Tentar de novo</Botao>
        </div>
      </div>
    );
  }
  if (carga.carregando) return <p className="text-suave">Carregando…</p>;
  if (itens.length === 0) return <p className="font-semibold">{vazio}</p>;
  return <div className="flex flex-col gap-3">{itens}</div>;
}

function CampoTotem({
  rotulo,
  valor,
  filtro,
  teclado,
  pronto,
  aoMudar,
  aoAvancar,
}: {
  rotulo: string;
  valor: string;
  filtro: (v: string) => string;
  teclado: "numerico" | "alfanumerico";
  pronto: boolean;
  aoMudar: (v: string) => void;
  aoAvancar: () => void;
}) {
  const enviar = (e: SubmitEvent) => {
    e.preventDefault();
    if (pronto) aoAvancar();
  };
  return (
    <form onSubmit={enviar} className="flex flex-col gap-4">
      <label className="flex flex-col gap-2 font-semibold">
        {rotulo}
        <input
          className={`${CLASSE_ENTRADA} min-h-16 text-3xl font-mono`}
          value={valor}
          inputMode="none"
          autoFocus
          autoComplete="off"
          onChange={(e) => {
            aoMudar(filtro(e.target.value));
          }}
        />
      </label>
      <TecladoTela
        tipo={teclado}
        aoDigitar={(c) => {
          aoMudar(filtro(valor + c));
        }}
        aoApagar={() => {
          aoMudar(valor.slice(0, -1));
        }}
      />
      <div>
        <Botao type="submit" variante="acao" className="w-full justify-center" disabled={!pronto}>
          Avançar
        </Botao>
      </div>
    </form>
  );
}

function Fluxo({ aoReiniciar }: { aoReiniciar: () => void }) {
  const [dados, setDados] = useState<Dados>(VAZIO);
  const [etapa, setEtapa] = useState<Etapa | "pronto">("tipo");
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<AgendamentoAutoatendimento | null>(null);
  const [toques, setToques] = useState(0);

  // Parada sem toque apaga tudo: o totem é público e guarda CPF digitado (spec 020 §6.3).
  useEffect(() => {
    const t = setTimeout(aoReiniciar, INATIVIDADE_MS);
    return () => {
      clearTimeout(t);
    };
  }, [toques, aoReiniciar]);

  const etapas: Etapa[] = [
    "tipo",
    "produto",
    "data",
    "faixa",
    "placa",
    "cpf",
    ...(dados.tipo === "DESCARGA" ? (["nota"] as const) : []),
    "conferir",
  ];
  const total = etapas.length;
  const indice = etapas.indexOf(etapa === "pronto" ? "conferir" : etapa) + 1;
  const voltar =
    indice > 1 && etapa !== "pronto"
      ? () => {
          setAviso("");
          setEtapa(etapas[indice - 2] ?? "tipo");
        }
      : undefined;
  const ir = (prox: Etapa, parcial: Partial<Dados> = {}) => {
    setDados((d) => ({ ...d, ...parcial }));
    setAviso("");
    setEtapa(prox);
  };
  const depoisDoCpf: Etapa = dados.tipo === "DESCARGA" ? "nota" : "conferir";

  const confirmar = () => {
    if (!dados.tipo || !dados.produto || !dados.faixa) return;
    setEnviando(true);
    setAviso("");
    criarAgendamentoAutoatendimento({
      placa: dados.placa,
      cpf: dados.cpf,
      tipo_operacao: dados.tipo,
      produto_id: dados.produto.id,
      data_prevista: dados.data,
      faixa_horario_id: dados.faixa.faixa_horario_id,
      ...(dados.tipo === "DESCARGA" ? { codigo_nota: dados.nota } : {}),
    }).then(
      (r) => {
        setResultado(r);
        setEtapa("pronto");
        setEnviando(false);
      },
      (e: unknown) => {
        const { texto, etapa: volta } = tratarErroEnvio(e);
        setAviso(texto);
        setEnviando(false);
        if (volta) setEtapa(volta);
      },
    );
  };

  const produtos = useCarga(
    () =>
      etapa === "produto"
        ? listarTodos({ listar: listarProdutosAutoatendimento })
        : Promise.resolve([]),
    `produtos/${etapa === "produto" ? "1" : "0"}`,
  );
  const disp = useCarga(
    () =>
      etapa === "faixa" && dados.data
        ? disponibilidadeAutoatendimento(dados.data)
        : Promise.resolve(null),
    `faixas/${etapa}/${dados.data}`,
  );

  const avisoBloco = aviso && (
    <p
      role="alert"
      className="flex items-center gap-2 border border-vermelho bg-claro p-3 font-semibold text-vermelho"
    >
      <SimboloEstado tipo="falha" />
      {aviso}
    </p>
  );

  let tela: ReactNode;
  if (etapa === "pronto" && resultado) {
    tela = (
      <section className="flex flex-col gap-6">
        <h1 className="flex items-center gap-3 text-4xl font-bold">
          <SimboloEstado tipo="ok" />
          Agendamento feito
        </h1>
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
          <dt className="text-suave">Número</dt>
          <dd className="font-semibold">{resultado.agendamento_id}</dd>
          <dt className="text-suave">Operação</dt>
          <dd className="font-semibold">
            {resultado.tipo_operacao === "CARGA" ? "Carga" : "Descarga"}
          </dd>
          <dt className="text-suave">Data</dt>
          <dd className="font-semibold">{formatarData(resultado.data_prevista)}</dd>
          <dt className="text-suave">Horário</dt>
          <dd className="font-semibold">
            {resultado.faixa_hora_inicio} às {resultado.faixa_hora_fim}
          </dd>
        </dl>
        <p className="text-suave">Esta tela volta ao início sozinha.</p>
        <div>
          <Botao variante="acao" className="w-full justify-center" onClick={aoReiniciar}>
            Novo agendamento
          </Botao>
        </div>
      </section>
    );
  } else if (etapa === "tipo") {
    tela = (
      <Passo titulo="O que você vai fazer?" indice={indice} total={total}>
        {avisoBloco}
        <div className="flex flex-col gap-3">
          {(["CARGA", "DESCARGA"] as const).map((t) => (
            <Botao
              key={t}
              variante="acao"
              className="justify-center"
              onClick={() => {
                ir("produto", { tipo: t });
              }}
            >
              {t === "CARGA" ? "Carga" : "Descarga"}
            </Botao>
          ))}
        </div>
      </Passo>
    );
  } else if (etapa === "produto") {
    tela = (
      <Passo titulo="Qual é o produto?" indice={indice} total={total} aoVoltar={voltar}>
        <Opcoes
          carga={produtos}
          vazio="Nenhum produto disponível. Fale com o operador."
          itens={(produtos.dados ?? []).map((p) => (
            <Botao
              key={p.id}
              variante="acao"
              className="justify-center"
              onClick={() => {
                ir("data", { produto: p });
              }}
            >
              {p.descricao}
            </Botao>
          ))}
        />
      </Passo>
    );
  } else if (etapa === "data") {
    tela = (
      <Passo titulo="Para qual dia?" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <div className="flex flex-col gap-3">
          {proximosDias(DIAS_A_FRENTE).map((d) => (
            <Botao
              key={d.data}
              variante="acao"
              className="justify-center"
              onClick={() => {
                ir("faixa", { data: d.data, faixa: null });
              }}
            >
              {d.texto}
            </Botao>
          ))}
        </div>
      </Passo>
    );
  } else if (etapa === "faixa") {
    const faixas = disp.dados?.itens ?? [];
    const sugerida = faixas.find((f) => f.vagas_livres > 0 && !f.encerrada);
    tela = (
      <Passo titulo="Qual horário?" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <Opcoes
          carga={disp}
          vazio="Sem faixa de horário neste dia. Escolha outro dia."
          itens={faixas.map((f) => {
            const livre = f.vagas_livres > 0 && !f.encerrada;
            const sufixo = f.encerrada
              ? "encerrada"
              : f.vagas_livres === 0
                ? "sem vaga"
                : `${String(f.vagas_livres)} ${f.vagas_livres === 1 ? "vaga" : "vagas"}`;
            return (
              <Botao
                key={f.faixa_horario_id}
                variante="acao"
                className="justify-center"
                disabled={!livre}
                onClick={() => {
                  ir("placa", { faixa: f });
                }}
              >
                {f.hora_inicio} às {f.hora_fim} · {sufixo}
                {f === sugerida ? " · Sugerida" : ""}
              </Botao>
            );
          })}
        />
        {!disp.carregando && disp.erro === undefined && faixas.length > 0 && !sugerida && (
          <p className="font-semibold">Sem vaga neste dia. Escolha outro dia.</p>
        )}
      </Passo>
    );
  } else if (etapa === "placa") {
    tela = (
      <Passo titulo="Qual é a placa do caminhão?" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <CampoTotem
          rotulo="Placa"
          valor={dados.placa}
          filtro={filtroPlaca}
          teclado="alfanumerico"
          pronto={dados.placa.trim() !== ""}
          aoMudar={(placa) => {
            setDados((d) => ({ ...d, placa }));
          }}
          aoAvancar={() => {
            ir("cpf");
          }}
        />
      </Passo>
    );
  } else if (etapa === "cpf") {
    tela = (
      <Passo titulo="Qual é o seu CPF?" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <CampoTotem
          rotulo="CPF (só números)"
          valor={dados.cpf}
          filtro={filtroCpf}
          teclado="numerico"
          pronto={dados.cpf.length === 11}
          aoMudar={(cpf) => {
            setDados((d) => ({ ...d, cpf }));
          }}
          aoAvancar={() => {
            ir(depoisDoCpf);
          }}
        />
      </Passo>
    );
  } else if (etapa === "nota") {
    tela = (
      <Passo titulo="Qual é o código da nota?" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <p className="text-suave">Passe o código da nota no leitor ou digite.</p>
        <CampoTotem
          rotulo="Código da nota"
          valor={dados.nota}
          filtro={filtroNota}
          teclado="alfanumerico"
          pronto={dados.nota.trim() !== ""}
          aoMudar={(nota) => {
            setDados((d) => ({ ...d, nota }));
          }}
          aoAvancar={() => {
            ir("conferir");
          }}
        />
      </Passo>
    );
  } else {
    tela = (
      <Passo titulo="Confira os dados" indice={indice} total={total} aoVoltar={voltar}>
        {avisoBloco}
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2">
          <dt className="text-suave">Operação</dt>
          <dd className="font-semibold">{dados.tipo === "CARGA" ? "Carga" : "Descarga"}</dd>
          <dt className="text-suave">Produto</dt>
          <dd className="font-semibold">{dados.produto?.descricao}</dd>
          <dt className="text-suave">Data</dt>
          <dd className="font-semibold">{formatarData(dados.data)}</dd>
          <dt className="text-suave">Horário</dt>
          <dd className="font-semibold">
            {dados.faixa?.hora_inicio} às {dados.faixa?.hora_fim}
          </dd>
          <dt className="text-suave">Placa</dt>
          <dd className="font-mono font-semibold">{dados.placa}</dd>
          <dt className="text-suave">CPF</dt>
          <dd className="font-mono font-semibold">{mascararCpf(dados.cpf)}</dd>
          {dados.tipo === "DESCARGA" && (
            <>
              <dt className="text-suave">Nota</dt>
              <dd className="font-mono font-semibold">{dados.nota}</dd>
            </>
          )}
        </dl>
        <div>
          <Botao
            variante="acao"
            className="w-full justify-center"
            onClick={confirmar}
            disabled={enviando}
          >
            {enviando ? "Enviando…" : "Confirmar agendamento"}
          </Botao>
        </div>
      </Passo>
    );
  }

  return (
    <div
      onPointerDownCapture={() => {
        setToques((n) => n + 1);
      }}
      onKeyDownCapture={() => {
        setToques((n) => n + 1);
      }}
    >
      {tela}
    </div>
  );
}

/** Autoatendimento do motorista, sem login (spec 020). */
export function PaginaAutoatendimento() {
  const [ciclo, setCiclo] = useState(0);
  return (
    <Fluxo
      key={ciclo}
      aoReiniciar={() => {
        setCiclo((c) => c + 1);
      }}
    />
  );
}
