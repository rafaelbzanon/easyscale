import { faixasHorario } from "../../api/agendamentos";
import type { ApiCadastro, DefCadastro } from "../cadastros/definicoes";

// Cast: mesma razão de `api` em cadastros/definicoes.ts.
export const FAIXAS: DefCadastro = {
  chave: "faixas",
  rotulo: "Faixas de horário",
  novo: "Nova faixa",
  api: faixasHorario as unknown as ApiCadastro,
  avisoInativo: "Faixa inativa não recebe agendamentos novos. Os que já existem continuam válidos.",
  campos: [
    { nome: "hora_inicio", rotulo: "Início", tipo: "hora", obrigatorio: true },
    { nome: "hora_fim", rotulo: "Fim", tipo: "hora", obrigatorio: true },
    { nome: "capacidade", rotulo: "Capacidade (vagas por dia)", tipo: "numero", obrigatorio: true },
  ],
  colunas: [
    { rotulo: "Início", valor: (i) => String(i.hora_inicio) },
    { rotulo: "Fim", valor: (i) => String(i.hora_fim) },
    { rotulo: "Capacidade", valor: (i) => String(i.capacidade) },
  ],
};
