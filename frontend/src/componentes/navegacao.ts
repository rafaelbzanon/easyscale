/** Itens do menu; cada um só aparece com a permissão (spec 017 §3.2). Acrescente na ordem do fluxo. */
export const ITENS_NAVEGACAO: { rota: string; rotulo: string; permissao: string }[] = [
  { rota: "/operacao", rotulo: "Operação", permissao: "CONSULTAR_OPERACAO" },
  { rota: "/dispositivos", rotulo: "Dispositivos", permissao: "CONSULTAR_OPERACAO" },
  { rota: "/diagnostico", rotulo: "Diagnóstico", permissao: "CONSULTAR_OPERACAO" },
  { rota: "/agendamentos", rotulo: "Agendamentos", permissao: "CONSULTAR_AGENDAMENTOS" },
  { rota: "/historico", rotulo: "Histórico", permissao: "CONSULTAR_OPERACAO" },
  { rota: "/cadastros", rotulo: "Cadastros", permissao: "CONSULTAR_CADASTROS" },
  { rota: "/usuarios", rotulo: "Usuários", permissao: "GERENCIAR_USUARIOS" },
];
