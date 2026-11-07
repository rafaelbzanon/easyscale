import { Link } from "react-router";
import { AreaAcoes } from "../../componentes/AreaAcoes";
import { formatarIdade, formatarPeso } from "../../componentes/formatar-peso";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { SimboloEstado } from "../../componentes/SimboloEstado";
import { useSessao } from "../../componentes/useSessao";
import type { EstadoOperacao } from "../../tipos/operacao";
import { Fila, Liberacoes } from "../operacao/PaginaOperacao";
import {
  indicadorAvaliacao,
  indicadorCancela,
  indicadorComando,
  indicadorComunicacao,
  indicadorIdentificacao,
  indicadorPosicao,
} from "../operacao/textos";
import { useCanalOperacao } from "../operacao/useCanalOperacao";
import { LiberarEntrada } from "./LiberarEntrada";

/** Modo do dispositivo em palavra e forma. Valor fora de REAL e SIMULADO é desconhecido, nunca simulado. */
function Modo({ valor }: { valor: unknown }) {
  const base =
    "inline-flex items-center gap-2 border-2 px-2 py-0.5 text-sm font-bold tracking-wide";
  if (valor === "REAL") {
    return (
      <span className={`${base} border-vermelho bg-vermelho text-claro`}>
        <SimboloEstado tipo="atencao" />
        REAL
      </span>
    );
  }
  if (valor === "SIMULADO") {
    return (
      <span className={`${base} border-azul bg-claro text-tinta`}>
        <SimboloEstado tipo="informacao" />
        SIMULADO
      </span>
    );
  }
  return (
    <span className={`${base} border-tinta bg-amarelo text-tinta`}>
      <SimboloEstado tipo="atencao" />
      MODO DESCONHECIDO
    </span>
  );
}

function Linha({
  nome,
  modo,
  children,
}: {
  nome: string;
  modo: unknown;
  children: React.ReactNode;
}) {
  return (
    <li className="flex flex-col gap-1 border-b border-fio py-3">
      <p className="flex flex-wrap items-center gap-3">
        <span className="text-lg font-bold">{nome}</span>
        <Modo valor={modo} />
      </p>
      {children}
    </li>
  );
}

const idade = (instante: string | null, agora: number) =>
  instante ? (
    <span className="text-sm text-suave">Informação de {formatarIdade(instante, agora)}</span>
  ) : null;

function Dispositivos({ estado, agora }: { estado: EstadoOperacao; agora: number }) {
  const { balanca, cancelas, posicao, identificacao } = estado.dispositivos;
  const avaliacao = indicadorAvaliacao(balanca);
  return (
    <section aria-label="Dispositivos" className="flex flex-col gap-1">
      <h2 className="text-sm font-bold tracking-wide text-suave uppercase">Dispositivos</h2>
      <ul className="flex flex-col">
        <Linha nome="Balança" modo={balanca.modo}>
          <IndicadorEstado {...indicadorComunicacao(balanca)} />
          {avaliacao && <IndicadorEstado {...avaliacao} />}
          {balanca.ultima_leitura && (
            <span className="text-sm">
              {formatarPeso(balanca.ultima_leitura.peso_kg)} · leitura, não é peso aceito ·{" "}
              {formatarIdade(balanca.ultima_leitura.lida_em, agora)}
            </span>
          )}
        </Linha>
        {cancelas.map((c) => {
          const comando = indicadorComando(c);
          return (
            <Linha
              key={c.cancela}
              nome={c.cancela === "ENTRADA" ? "Cancela de entrada" : "Cancela de saída"}
              modo={c.modo}
            >
              <IndicadorEstado {...indicadorCancela(c)} />
              {comando && <IndicadorEstado {...comando} />}
              {idade(c.estado_em, agora)}
            </Linha>
          );
        })}
        <Linha nome="Câmera de posição" modo={posicao.modo}>
          <IndicadorEstado {...indicadorPosicao(posicao)} />
          {idade(posicao.analisada_em, agora)}
        </Linha>
        <Linha nome="Identificação de placa" modo={identificacao.modo}>
          <IndicadorEstado {...indicadorIdentificacao(identificacao)} />
          {idade(identificacao.analisada_em, agora)}
        </Linha>
      </ul>
    </section>
  );
}

/** Spec 024. Quem decide é o backend; a tela só mostra e pede (S-5). */
export function PaginaDispositivos() {
  const canal = useCanalOperacao();
  const { estado, desatualizada } = canal;
  const { permissoes } = useSessao();
  const emIntervencao =
    estado?.pesagens_abertas.filter((p) => p.situacao === "AGUARDANDO_INTERVENCAO").length ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="text-2xl font-bold">Dispositivos</h1>
        {!canal.sincronizado && !canal.canalFechado ? (
          <IndicadorEstado tipo="atencao" texto="Sincronizando…" />
        ) : desatualizada ? (
          <IndicadorEstado tipo="atencao" texto="Tela desatualizada" />
        ) : (
          <IndicadorEstado tipo="ok" texto="Atualizada" />
        )}
        <Link to="/operacao" className="font-semibold text-azul underline">
          Ver a tela de operação
        </Link>
      </div>
      {estado ? (
        <>
          {/* Desatualizada: dados esmaecidos para não parecerem atuais (ADR-0005 §4.4). */}
          <div className={desatualizada ? "opacity-55" : undefined}>
            <Dispositivos estado={estado} agora={canal.agora} />
          </div>
          <AreaAcoes bloqueada={desatualizada}>
            <div className="flex w-full flex-col gap-6">
              <p className="font-semibold">
                {emIntervencao === 0 ? (
                  <IndicadorEstado tipo="ok" texto="Nenhuma pesagem aguardando intervenção" />
                ) : (
                  <IndicadorEstado
                    tipo="atencao"
                    texto={`${String(emIntervencao)} ${emIntervencao === 1 ? "pesagem aguardando" : "pesagens aguardando"} intervenção`}
                  />
                )}
              </p>
              <Fila pesagens={estado.pesagens_abertas} aoResponder={canal.aplicarPesagem} />
              {estado.liberacoes_caminhao.length > 0 && (
                <Liberacoes liberacoes={estado.liberacoes_caminhao} estado={estado} />
              )}
              {permissoes.includes("INTERVIR_OPERACAO") && (
                <LiberarEntrada
                  leitura={estado.ultima_leitura_placa}
                  aoLiberar={canal.aplicarPesagem}
                />
              )}
            </div>
          </AreaAcoes>
        </>
      ) : (
        <p className="text-suave">Carregando o estado da operação…</p>
      )}
    </div>
  );
}
