import { useState, type SubmitEvent } from "react";
import { agendamentos } from "../../api/agendamentos";
import { ErroRequisicao } from "../../api/cliente-api";
import { listarTodos } from "../../api/listar-todos";
import { liberarEntrada } from "../../api/operacao";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { CampoFormulario } from "../../componentes/CampoFormulario";
import { formatarHora } from "../../componentes/formatar-peso";
import { IndicadorEstado } from "../../componentes/IndicadorEstado";
import { MensagemErro } from "../../componentes/MensagemErro";
import { useCarga } from "../../componentes/useCarga";
import type { LeituraPlaca, Pesagem } from "../../tipos/operacao";
import { hoje } from "../agendamentos/formatos";
import { MOTIVO_NAO_AUTORIZACAO } from "../operacao/textos";

// Spec 009 §5.3: motivos que a liberação manual pode substituir. Só esconde o botão; o backend recusa o resto.
const SUBSTITUIVEIS = [
  "FALHA_IMAGEM",
  "FALHA_LEITOR",
  "SEM_CANDIDATO",
  "PLACA_INVALIDA",
  "AMBIGUA",
  "CONFIANCA_BAIXA",
  "ANTES_DA_FAIXA",
];

// Spec 009 §6.4.
const MENSAGEM_CONFLITO: Record<string, string> = {
  LEITURA_DESATUALIZADA: "Chegou uma leitura mais nova. Confira a última placa lida.",
  LEITURA_NAO_LIBERAVEL: "Essa leitura já foi liberada ou não precisa de liberação.",
  MOTIVO_NAO_SUBSTITUIVEL: "Esse motivo não pode ser liberado aqui.",
  VEICULO_INATIVO: "O veículo do agendamento está inativo.",
  MOTORISTA_INATIVO: "O motorista do agendamento está inativo.",
  OPERACAO_JA_ABERTA: "Esse veículo já tem uma operação aberta.",
  SEM_AGENDAMENTO: "O agendamento escolhido não vale para hoje.",
};
const textoConflito = (erro: unknown) =>
  erro instanceof ErroRequisicao && erro.status === 409
    ? (erro.erro?.campos.map((c) => MENSAGEM_CONFLITO[c.codigo]).find(Boolean) ?? null)
    : null;

function Formulario({
  leitura,
  aoLiberar,
}: {
  leitura: LeituraPlaca;
  aoLiberar: (p: Pesagem) => void;
}) {
  const [data] = useState(hoje);
  const lista = useCarga(
    () =>
      listarTodos({
        listar: (f) =>
          agendamentos.listar({ ...f, status: "AGENDADO", data_inicio: data, data_fim: data }),
      }),
    `agendados/${data}`,
  );
  const [agendamentoId, setAgendamentoId] = useState("");
  const [motivo, setMotivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);
  const [feito, setFeito] = useState(false);

  if (feito) {
    return (
      <p role="status" className="flex items-center gap-2 font-semibold">
        <IndicadorEstado
          tipo="ok"
          texto="Entrada liberada para o agendamento. A cancela abre quando a balança estiver livre."
        />
      </p>
    );
  }
  if (lista.erro !== undefined) {
    return <MensagemErro erro={lista.erro} aoTentarNovamente={lista.recarregar} />;
  }
  if (!lista.dados) return <p className="text-suave">Carregando…</p>;
  if (lista.dados.length === 0) {
    return <p className="font-semibold">Nenhum agendamento para hoje. Crie o agendamento antes.</p>;
  }

  const enviar = (e: SubmitEvent) => {
    e.preventDefault();
    setEnviando(true);
    setErro(null);
    liberarEntrada(leitura.id, {
      agendamento_id: Number(agendamentoId),
      motivo: motivo.trim(),
    }).then(
      (p) => {
        setFeito(true);
        aoLiberar(p);
      },
      (e: unknown) => {
        setErro(e);
        setEnviando(false);
      },
    );
  };

  return (
    <form
      onSubmit={enviar}
      className="flex max-w-2xl flex-col gap-3 border border-fio bg-claro p-3"
    >
      <p className="text-sm">
        Cria a pesagem para o agendamento escolhido. A entrada só abre depois, com a balança livre.
      </p>
      <CampoFormulario rotulo="Agendamento de hoje" obrigatorio>
        <select
          className={CLASSE_ENTRADA}
          required
          value={agendamentoId}
          onChange={(e) => {
            setAgendamentoId(e.target.value);
          }}
        >
          <option value="">Escolha…</option>
          {lista.dados.map((a) => (
            <option key={a.id} value={a.id}>
              {a.placa} · {a.motorista_nome} · {a.faixa_hora_inicio}–{a.faixa_hora_fim} ·{" "}
              {a.tipo_operacao === "CARGA" ? "Carga" : "Descarga"}
            </option>
          ))}
        </select>
      </CampoFormulario>
      <CampoFormulario rotulo="Motivo" obrigatorio>
        <input
          className={CLASSE_ENTRADA}
          required
          maxLength={200}
          value={motivo}
          onChange={(e) => {
            setMotivo(e.target.value);
          }}
        />
      </CampoFormulario>
      {erro !== null && <MensagemErro erro={erro} texto={textoConflito(erro)} />}
      <Botao
        type="submit"
        variante="acao"
        className="self-start"
        disabled={enviando || agendamentoId === "" || motivo.trim() === ""}
      >
        {enviando ? "Enviando…" : "Liberar entrada"}
      </Botao>
    </form>
  );
}

/** Liberação manual de entrada (RN-016, spec 024 §6.4): age sobre a última leitura de placa. */
export function LiberarEntrada({
  leitura,
  aoLiberar,
}: {
  leitura: LeituraPlaca | null;
  aoLiberar: (p: Pesagem) => void;
}) {
  const motivo = leitura?.motivo ?? null;
  let corpo;
  if (!leitura) {
    corpo = <p className="text-suave">Nenhuma placa lida.</p>;
  } else if (leitura.decisao !== "NAO_AUTORIZADA") {
    corpo = <p className="text-suave">A última leitura foi autorizada. Não há o que liberar.</p>;
  } else if (leitura.pesagem_id !== null) {
    corpo = (
      <p className="font-semibold">Essa leitura já gerou a pesagem nº {leitura.pesagem_id}.</p>
    );
  } else if (motivo === null || !SUBSTITUIVEIS.includes(motivo)) {
    corpo = (
      <p className="font-semibold">
        Esse motivo não pode ser liberado aqui. Resolva o cadastro ou o agendamento.
      </p>
    );
  } else {
    corpo = <Formulario key={leitura.id} leitura={leitura} aoLiberar={aoLiberar} />;
  }
  return (
    <section
      aria-label="Liberação manual de entrada"
      className="flex flex-col gap-2 border-t border-fio pt-3"
    >
      <h2 className="text-sm font-bold tracking-wide text-suave uppercase">
        Liberação manual de entrada
      </h2>
      {leitura && (
        <p className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <span className="font-mono text-xl font-bold">
            {leitura.placa_normalizada ?? "Sem placa"}
          </span>
          <span>
            {leitura.decisao === "NAO_AUTORIZADA"
              ? `Não autorizada${motivo ? `: ${MOTIVO_NAO_AUTORIZACAO[motivo]}` : ""}`
              : leitura.decisao === "AUTORIZADA"
                ? "Autorizada"
                : "Retorno aceito"}
          </span>
          <span className="text-sm text-suave">
            {leitura.confianca !== null && `Confiança ${leitura.confianca} · `}
            {formatarHora(leitura.decidida_em)}
            {leitura.imagem_id !== null && " · imagem salva"}
          </span>
        </p>
      )}
      {corpo}
    </section>
  );
}
