import { useState, type SubmitEvent } from "react";
import { agendamentos, faixasHorario } from "../../api/agendamentos";
import { motoristas, produtos, transportadoras, veiculos } from "../../api/cadastros";
import { ErroRequisicao } from "../../api/cliente-api";
import { listarTodos } from "../../api/listar-todos";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { CampoFormulario } from "../../componentes/CampoFormulario";
import { MensagemErro } from "../../componentes/MensagemErro";
import { textoCodigo } from "../../componentes/texto-codigo";
import { useCarga } from "../../componentes/useCarga";
import type {
  Agendamento,
  AgendamentoAlteracao,
  AgendamentoCriacao,
} from "../../tipos/agendamentos";
import type { Motorista, Produto, Transportadora, Veiculo } from "../../tipos/cadastros";
import { emTexto, type DefCampo, type Registro } from "../cadastros/definicoes";
import { montar } from "../cadastros/FormularioCadastro";
import { hoje } from "./formatos";

const CAMPOS: DefCampo[] = [
  { nome: "veiculo_id", rotulo: "Veículo", tipo: "numero" },
  { nome: "motorista_id", rotulo: "Motorista", tipo: "numero" },
  { nome: "transportadora_id", rotulo: "Transportadora", tipo: "numero" },
  { nome: "produto_id", rotulo: "Produto", tipo: "numero" },
  { nome: "tipo_operacao", rotulo: "Tipo de operação" },
  { nome: "data_prevista", rotulo: "Data prevista", tipo: "data" },
  { nome: "faixa_horario_id", rotulo: "Faixa de horário", tipo: "numero" },
  { nome: "codigo_nota", rotulo: "Código da nota" },
  { nome: "observacao", rotulo: "Observação" },
];

interface Apoios {
  veiculos: Veiculo[];
  motoristas: Motorista[];
  transportadoras: Transportadora[];
  produtos: Produto[];
}

const carregarApoios = async (): Promise<Apoios> => {
  const [v, m, t, p] = await Promise.all([
    listarTodos(veiculos),
    listarTodos(motoristas),
    listarTodos(transportadoras),
    listarTodos(produtos),
  ]);
  return { veiculos: v, motoristas: m, transportadoras: t, produtos: p };
};

function Escolha<T extends { id: number; ativo: boolean }>({
  valor,
  itens,
  rotulo,
  invalido,
  obrigatorio = false,
  aoMudar,
}: {
  valor: string;
  itens: T[];
  rotulo: (i: T) => string;
  invalido: boolean;
  obrigatorio?: boolean;
  aoMudar: (v: string) => void;
}) {
  // Só ativos; o valor atual continua na lista mesmo se o cadastro estiver inativo.
  const lista = itens.filter((i) => i.ativo || String(i.id) === valor);
  return (
    <select
      className={CLASSE_ENTRADA}
      value={valor}
      required={obrigatorio}
      aria-invalid={invalido || undefined}
      onChange={(e) => {
        aoMudar(e.target.value);
      }}
    >
      <option value="">{obrigatorio ? "Escolha…" : "Nenhum"}</option>
      {lista.map((i) => (
        <option key={i.id} value={i.id}>
          {rotulo(i)}
        </option>
      ))}
    </select>
  );
}

function Campos({
  item,
  apoios,
  aoSalvar,
  aoVoltar,
}: {
  item: Agendamento | null;
  apoios: Apoios;
  aoSalvar: (a: Agendamento) => void;
  aoVoltar: () => void;
}) {
  const [valores, setValores] = useState<Record<string, string>>(() => ({
    ...Object.fromEntries(
      CAMPOS.map((c) => [c.nome, item ? emTexto(item[c.nome as keyof Agendamento]) : ""]),
    ),
    ...(item ? {} : { data_prevista: hoje() }),
  }));
  // `null`: o usuário ainda não escolheu; vale a sugestão (spec 019 §6.2 item 4).
  const [faixaEscolhida, setFaixaEscolhida] = useState<string | null>(
    item ? String(item.faixa_horario_id) : null,
  );
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  const data = valores.data_prevista ?? "";
  const disponibilidade = useCarga(
    () => (data ? faixasHorario.disponibilidade(data) : Promise.resolve(null)),
    `disponibilidade/${data}`,
  );
  const faixas = disponibilidade.dados?.itens ?? [];
  const sugerida = faixas.find((f) => f.vagas_livres > 0 && !f.encerrada);
  const faixa = faixaEscolhida ?? (sugerida ? String(sugerida.faixa_horario_id) : "");

  const campoComErro = new Map(
    (erro instanceof ErroRequisicao ? (erro.erro?.campos ?? []) : []).map((c) => [
      c.campo,
      c.codigo,
    ]),
  );
  const erroDe = (nome: string) => {
    const codigo = campoComErro.get(nome);
    return codigo === undefined ? undefined : textoCodigo(codigo);
  };
  const mudar = (nome: string, v: string) => {
    setValores((atual) => ({ ...atual, [nome]: v }));
  };
  const escolherVeiculo = (v: string) => {
    mudar("veiculo_id", v);
    const veiculo = apoios.veiculos.find((x) => String(x.id) === v);
    if (item || !veiculo) return;
    // Pré-preenchimento: quem agenda confere e pode trocar (spec 008 §6.8).
    setValores((atual) => ({
      ...atual,
      veiculo_id: v,
      transportadora_id:
        veiculo.transportadora_id === null
          ? (atual.transportadora_id ?? "")
          : String(veiculo.transportadora_id),
      motorista_id:
        veiculo.motorista_padrao_id === null
          ? (atual.motorista_id ?? "")
          : String(veiculo.motorista_padrao_id),
    }));
  };

  const descarga = valores.tipo_operacao === "DESCARGA";
  const enviar = (e: SubmitEvent) => {
    e.preventDefault();
    const dados = montar(
      CAMPOS,
      {
        ...valores,
        faixa_horario_id: faixa,
        codigo_nota: descarga ? (valores.codigo_nota ?? "") : "",
      },
      item as unknown as Registro | null,
    );
    if (item && Object.keys(dados).length === 0) {
      aoVoltar();
      return;
    }
    setEnviando(true);
    (item
      ? agendamentos.alterar(item.id, dados as AgendamentoAlteracao)
      : agendamentos.criar(dados as unknown as AgendamentoCriacao)
    ).then(aoSalvar, (e: unknown) => {
      setErro(e);
      setEnviando(false);
      const codigos =
        e instanceof ErroRequisicao ? (e.erro?.campos.map((c) => c.codigo) ?? []) : [];
      // A vaga pode ter acabado; mostra a disponibilidade atual.
      if (
        ["FAIXA_SEM_VAGA", "FAIXA_ENCERRADA", "SEM_FAIXA_DISPONIVEL"].some((c) =>
          codigos.includes(c),
        )
      ) {
        setFaixaEscolhida(null);
        disponibilidade.recarregar();
      }
    });
  };

  const semVaga = data !== "" && disponibilidade.dados && !sugerida && faixaEscolhida === null;
  return (
    <form onSubmit={enviar} className="mb-6 flex flex-col gap-4 border border-fio p-4">
      <h2 className="text-lg font-bold">{item ? "Editar agendamento" : "Novo agendamento"}</h2>
      {erro !== null && <MensagemErro erro={erro} />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <CampoFormulario rotulo="Veículo" obrigatorio erro={erroDe("veiculo_id")}>
          <Escolha
            valor={valores.veiculo_id ?? ""}
            itens={apoios.veiculos}
            rotulo={(i: Veiculo) => i.placa}
            invalido={campoComErro.has("veiculo_id")}
            obrigatorio
            aoMudar={escolherVeiculo}
          />
        </CampoFormulario>
        <CampoFormulario rotulo="Motorista" obrigatorio erro={erroDe("motorista_id")}>
          <Escolha
            valor={valores.motorista_id ?? ""}
            itens={apoios.motoristas}
            rotulo={(i: Motorista) => `${i.nome} (${i.cpf_mascarado})`}
            invalido={campoComErro.has("motorista_id")}
            obrigatorio
            aoMudar={(v) => {
              mudar("motorista_id", v);
            }}
          />
        </CampoFormulario>
        <CampoFormulario rotulo="Transportadora" erro={erroDe("transportadora_id")}>
          <Escolha
            valor={valores.transportadora_id ?? ""}
            itens={apoios.transportadoras}
            rotulo={(i: Transportadora) => i.razao_social}
            invalido={campoComErro.has("transportadora_id")}
            aoMudar={(v) => {
              mudar("transportadora_id", v);
            }}
          />
        </CampoFormulario>
        <CampoFormulario rotulo="Produto" obrigatorio erro={erroDe("produto_id")}>
          <Escolha
            valor={valores.produto_id ?? ""}
            itens={apoios.produtos}
            rotulo={(i: Produto) => i.descricao}
            invalido={campoComErro.has("produto_id")}
            obrigatorio
            aoMudar={(v) => {
              mudar("produto_id", v);
            }}
          />
        </CampoFormulario>
        <CampoFormulario rotulo="Tipo de operação" obrigatorio erro={erroDe("tipo_operacao")}>
          <select
            className={CLASSE_ENTRADA}
            required
            value={valores.tipo_operacao ?? ""}
            aria-invalid={campoComErro.has("tipo_operacao") || undefined}
            onChange={(e) => {
              mudar("tipo_operacao", e.target.value);
            }}
          >
            <option value="">Escolha…</option>
            <option value="CARGA">Carga</option>
            <option value="DESCARGA">Descarga</option>
          </select>
        </CampoFormulario>
        <CampoFormulario rotulo="Data prevista" obrigatorio erro={erroDe("data_prevista")}>
          <input
            type="date"
            className={CLASSE_ENTRADA}
            required
            value={data}
            aria-invalid={campoComErro.has("data_prevista") || undefined}
            onChange={(e) => {
              mudar("data_prevista", e.target.value);
              setFaixaEscolhida(null);
            }}
          />
        </CampoFormulario>
        <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-3">
          {disponibilidade.erro !== undefined ? (
            <MensagemErro
              erro={disponibilidade.erro}
              aoTentarNovamente={disponibilidade.recarregar}
            />
          ) : (
            <CampoFormulario
              rotulo="Faixa de horário"
              obrigatorio
              erro={erroDe("faixa_horario_id")}
            >
              <select
                className={CLASSE_ENTRADA}
                required
                value={faixa}
                disabled={disponibilidade.carregando}
                aria-invalid={campoComErro.has("faixa_horario_id") || undefined}
                onChange={(e) => {
                  setFaixaEscolhida(e.target.value);
                }}
              >
                <option value="">{disponibilidade.carregando ? "Carregando…" : "Escolha…"}</option>
                {faixas.map((f) => {
                  // Na edição, a faixa atual segue válida mesmo cheia: ela já conta a própria vaga.
                  const atual =
                    item !== null &&
                    f.faixa_horario_id === item.faixa_horario_id &&
                    data === item.data_prevista;
                  const sem = (f.vagas_livres === 0 || f.encerrada) && !atual;
                  return (
                    <option key={f.faixa_horario_id} value={f.faixa_horario_id} disabled={sem}>
                      {f.hora_inicio}–{f.hora_fim} · {f.vagas_livres}{" "}
                      {f.vagas_livres === 1 ? "vaga" : "vagas"}
                      {f.encerrada ? " · encerrada" : f.vagas_livres === 0 ? " · sem vaga" : ""}
                    </option>
                  );
                })}
              </select>
            </CampoFormulario>
          )}
          {faixaEscolhida === null && sugerida && (
            <p className="text-sm text-suave">
              Sugerida: primeira faixa com vaga. Confira ou escolha outra.
            </p>
          )}
          {semVaga && <p className="text-sm font-semibold">Sem vaga neste dia.</p>}
        </div>
        {descarga && (
          <CampoFormulario rotulo="Código da nota" erro={erroDe("codigo_nota")}>
            <input
              className={CLASSE_ENTRADA}
              maxLength={100}
              value={valores.codigo_nota ?? ""}
              aria-invalid={campoComErro.has("codigo_nota") || undefined}
              onChange={(e) => {
                mudar("codigo_nota", e.target.value);
              }}
            />
          </CampoFormulario>
        )}
        <CampoFormulario rotulo="Observação" erro={erroDe("observacao")}>
          <input
            className={CLASSE_ENTRADA}
            maxLength={200}
            value={valores.observacao ?? ""}
            onChange={(e) => {
              mudar("observacao", e.target.value);
            }}
          />
        </CampoFormulario>
      </div>
      <div className="flex flex-wrap gap-2 border-t border-fio pt-3">
        <Botao
          type="submit"
          variante="acao"
          disabled={enviando || disponibilidade.carregando || faixa === ""}
        >
          {enviando ? "Salvando…" : item ? "Salvar" : "Criar agendamento"}
        </Botao>
        <Botao onClick={aoVoltar} disabled={enviando}>
          Voltar
        </Botao>
      </div>
    </form>
  );
}

/** Carrega o item (na edição) e as listas de escolha, e abre o formulário. */
export function FormularioAgendamento({
  id,
  aoSalvar,
  aoVoltar,
}: {
  id: number | null;
  aoSalvar: (a: Agendamento) => void;
  aoVoltar: () => void;
}) {
  const dados = useCarga(
    async () => ({
      apoios: await carregarApoios(),
      item: id === null ? null : await agendamentos.obter(id),
    }),
    `formulario/${String(id)}`,
  );
  if (dados.erro !== undefined)
    return <MensagemErro erro={dados.erro} aoTentarNovamente={dados.recarregar} />;
  if (!dados.dados) return <p className="mb-6 text-suave">Carregando…</p>;
  const { apoios, item } = dados.dados;
  return <Campos item={item} apoios={apoios} aoSalvar={aoSalvar} aoVoltar={aoVoltar} />;
}
