import { useState, type SubmitEvent } from "react";
import { ErroRequisicao } from "../../api/cliente-api";
import { Botao } from "../../componentes/Botao";
import { CLASSE_ENTRADA } from "../../componentes/Campo";
import { CampoFormulario } from "../../componentes/CampoFormulario";
import { textoCodigo } from "../../componentes/texto-codigo";
import { MensagemErro } from "../../componentes/MensagemErro";
import { useCarga } from "../../componentes/useCarga";
import {
  APOIOS,
  emTexto,
  type Apoio,
  type DefCadastro,
  type DefCampo,
  type Registro,
} from "./definicoes";

export type Opcoes = Record<Apoio, Registro[]>;

const eApoio = (c: DefCampo) =>
  c.tipo === "transportadoras" || c.tipo === "tiposVeiculo" || c.tipo === "motoristas";
const eNumero = (c: DefCampo) => c.tipo === "numero" || eApoio(c);

const valorInicial = (c: DefCampo, item: Registro | null) => {
  return emTexto(item?.[c.nome]);
};

/** Só os campos alterados na edição (PATCH); todos os preenchidos na criação (spec 018 §6.2). */
export function montar(campos: DefCampo[], valores: Record<string, string>, item: Registro | null) {
  const dados: Record<string, unknown> = {};
  for (const campo of campos) {
    const bruto = valores[campo.nome] ?? "";
    if (item && bruto === valorInicial(campo, item)) continue;
    const limpo = campo.limpar ? campo.limpar(bruto.trim()) : bruto.trim();
    if (limpo === "") {
      if (item) dados[campo.nome] = null;
    } else {
      dados[campo.nome] = eNumero(campo) ? Number(limpo) : limpo;
    }
  }
  return dados;
}

function Controle({
  campo,
  valor,
  opcoes,
  invalido,
  aoMudar,
}: {
  campo: DefCampo;
  valor: string;
  opcoes: Opcoes;
  invalido: boolean;
  aoMudar: (v: string) => void;
}) {
  const classe = `${CLASSE_ENTRADA} ${campo.nome === "placa" ? "font-mono" : ""}`;
  const comum = {
    value: valor,
    required: campo.obrigatorio,
    "aria-invalid": invalido || undefined,
  };
  if (
    campo.tipo === "transportadoras" ||
    campo.tipo === "tiposVeiculo" ||
    campo.tipo === "motoristas"
  ) {
    const { rotulo } = APOIOS[campo.tipo];
    // Só ativos; o valor atual continua na lista mesmo se o cadastro estiver inativo.
    const lista = opcoes[campo.tipo].filter((i) => i.ativo || String(i.id) === valor);
    return (
      <select
        {...comum}
        className={classe}
        onChange={(e) => {
          aoMudar(e.target.value);
        }}
      >
        <option value="">{campo.obrigatorio ? "Escolha…" : "Nenhum"}</option>
        {lista.map((i) => (
          <option key={i.id} value={i.id}>
            {rotulo(i)}
            {i.ativo ? "" : " (inativo)"}
          </option>
        ))}
      </select>
    );
  }
  return (
    <input
      {...comum}
      className={classe}
      type={
        campo.tipo === "numero" ? "number" : campo.tipo === "hora" ? "time" : (campo.tipo ?? "text")
      }
      min={campo.tipo === "numero" ? 1 : undefined}
      maxLength={campo.max}
      onChange={(e) => {
        aoMudar(e.target.value);
      }}
    />
  );
}

function Campos({
  def,
  item,
  opcoes,
  aoSalvar,
  aoCancelar,
}: {
  def: DefCadastro;
  item: Registro | null;
  opcoes: Opcoes;
  aoSalvar: () => void;
  aoCancelar: () => void;
}) {
  const [valores, setValores] = useState<Record<string, string>>(() =>
    Object.fromEntries(def.campos.map((c) => [c.nome, valorInicial(c, item)])),
  );
  const [ativo, setAtivo] = useState(item?.ativo ?? true);
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  const campoComErro = new Map(
    (erro instanceof ErroRequisicao ? (erro.erro?.campos ?? []) : []).map((c) => [
      c.campo,
      c.codigo,
    ]),
  );
  const desativando = item?.ativo === true && !ativo;

  const enviar = (e: SubmitEvent) => {
    e.preventDefault();
    const dados = montar(def.campos, valores, item);
    if (item && ativo !== item.ativo) dados.ativo = ativo;
    if (item && Object.keys(dados).length === 0) {
      aoCancelar();
      return;
    }
    setEnviando(true);
    (item ? def.api.alterar(item.id, dados) : def.api.criar(dados)).then(aoSalvar, (e: unknown) => {
      setErro(e);
      setEnviando(false);
    });
  };

  return (
    <form onSubmit={enviar} className="mb-6 flex flex-col gap-4 border border-fio p-4">
      <h2 className="text-lg font-bold">
        {item ? `Editar: ${def.rotulo.toLowerCase()}` : def.novo}
      </h2>
      {erro !== null && <MensagemErro erro={erro} />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {def.campos.map((campo) => {
          const codigo = campoComErro.get(campo.nome);
          return (
            <CampoFormulario
              key={campo.nome}
              rotulo={campo.rotulo}
              obrigatorio={campo.obrigatorio}
              erro={codigo === undefined ? undefined : textoCodigo(codigo)}
            >
              <Controle
                campo={campo}
                valor={valores[campo.nome] ?? ""}
                opcoes={opcoes}
                invalido={codigo !== undefined}
                aoMudar={(v) => {
                  setValores((atual) => ({ ...atual, [campo.nome]: v }));
                }}
              />
            </CampoFormulario>
          );
        })}
      </div>
      {item && (
        <div className="flex flex-col gap-2">
          <label className="flex items-center gap-2 font-semibold">
            <input
              type="checkbox"
              className="size-5"
              checked={ativo}
              onChange={(e) => {
                setAtivo(e.target.checked);
              }}
            />
            Cadastro ativo
          </label>
          {!ativo && (
            <p className="text-sm text-suave">
              {def.avisoInativo ??
                "Cadastro inativo não entra em novos agendamentos e não é autorizado na entrada."}
            </p>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-2 border-t border-fio pt-3">
        <Botao type="submit" variante="acao" disabled={enviando}>
          {enviando ? "Salvando…" : desativando ? "Salvar e desativar" : "Salvar"}
        </Botao>
        <Botao onClick={aoCancelar} disabled={enviando}>
          Cancelar
        </Botao>
      </div>
    </form>
  );
}

/** Busca o item (o administrador recebe o CPF completo só aqui) e abre o formulário. */
export function FormularioCadastro({
  def,
  id,
  opcoes,
  aoSalvar,
  aoCancelar,
}: {
  def: DefCadastro;
  id: number | null;
  opcoes: Opcoes;
  aoSalvar: () => void;
  aoCancelar: () => void;
}) {
  const item = useCarga(
    () => (id === null ? Promise.resolve(null) : def.api.obter(id)),
    `${def.chave}/${String(id)}`,
  );
  if (item.erro !== undefined)
    return <MensagemErro erro={item.erro} aoTentarNovamente={item.recarregar} />;
  if (item.carregando) return <p className="mb-6 text-suave">Carregando…</p>;
  return (
    <Campos
      def={def}
      item={item.dados ?? null}
      opcoes={opcoes}
      aoSalvar={aoSalvar}
      aoCancelar={aoCancelar}
    />
  );
}
