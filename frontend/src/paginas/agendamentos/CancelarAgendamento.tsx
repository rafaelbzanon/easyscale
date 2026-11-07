import { useState, type SubmitEvent } from "react";
import { agendamentos } from "../../api/agendamentos";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { CampoFormulario } from "../../componentes/CampoFormulario";
import { MensagemErro } from "../../componentes/MensagemErro";
import type { Agendamento } from "../../tipos/agendamentos";
import { formatarData } from "./formatos";

/** Cancelamento com motivo; mostra o efeito antes de enviar (spec 019 §6.4). */
export function CancelarAgendamento({
  agendamento,
  aoConcluir,
  aoFalhar,
  aoVoltar,
}: {
  agendamento: Agendamento;
  aoConcluir: () => void;
  aoFalhar: () => void;
  aoVoltar: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = (e: SubmitEvent) => {
    e.preventDefault();
    setEnviando(true);
    agendamentos
      .cancelar(agendamento.id, { motivo: motivo.trim() })
      .then(aoConcluir, (e: unknown) => {
        setErro(e);
        setEnviando(false);
        aoFalhar(); // o status pode ter mudado (409 STATUS_NAO_PERMITE): recarrega a lista
      });
  };

  return (
    <form onSubmit={enviar} className="mb-6 flex flex-col gap-4 border border-fio p-4">
      <h2 className="text-lg font-bold">Cancelar agendamento</h2>
      <p>
        Isto cancela o agendamento do veículo <span className="font-mono">{agendamento.placa}</span>{" "}
        em {formatarData(agendamento.data_prevista)}. A vaga da faixa é liberada.
      </p>
      {erro !== null && <MensagemErro erro={erro} />}
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
      <div className="flex flex-wrap gap-2 border-t border-fio pt-3">
        <Botao type="submit" variante="acao" disabled={enviando || motivo.trim() === ""}>
          {enviando ? "Cancelando…" : "Confirmar cancelamento"}
        </Botao>
        <Botao onClick={aoVoltar} disabled={enviando}>
          Voltar
        </Botao>
      </div>
    </form>
  );
}
