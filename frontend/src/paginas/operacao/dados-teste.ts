// Só para testes: objetos completos da spec 009, com valores sintéticos (S-6).
import type { EstadoOperacao, LiberacaoCaminhao, Pesagem } from "../../tipos/operacao";

export const T0 = "2026-11-07T10:00:00-03:00";
export const depois = (s: number) => new Date(Date.parse(T0) + s * 1000).toISOString();

export const pesagem = (campos: Partial<Pesagem> = {}): Pesagem => ({
  id: 12,
  versao: 3,
  situacao: "POSICIONADA_INICIAL",
  situacao_anterior: null,
  motivo_intervencao: null,
  comando_pendente: null,
  acoes_disponiveis: [],
  ocupa_balanca: true,
  aguarda_liberacao_balanca: false,
  liberacao_manual: false,
  agendamento_id: 31,
  agendamento_status: "EM_ANDAMENTO",
  tipo_operacao: "CARGA",
  placa: "ABC1D23",
  motorista_nome: "João Teste",
  transportadora_razao_social: null,
  produto_descricao: "Soja",
  data_prevista: "2026-11-07",
  faixa_hora_inicio: "08:00",
  faixa_hora_fim: "10:00",
  peso_inicial_kg: null,
  peso_inicial_em: null,
  peso_final_kg: null,
  peso_final_em: null,
  peso_liquido_kg: null,
  classificacao: null,
  criado_em: T0,
  atualizado_em: T0,
  ...campos,
});

export const liberacao = (campos: Partial<LiberacaoCaminhao> = {}): LiberacaoCaminhao => ({
  pesagem_id: 40,
  etapa: "PENDENTE",
  motivo_falha: null,
  pedido_por: null,
  pedido_por_nome: null,
  motivo: null,
  pedida_em: null,
  atualizada_em: T0,
  ...campos,
});

export const estadoOperacao = (campos: Partial<EstadoOperacao> = {}): EstadoOperacao => ({
  gerado_em: T0,
  tempo_real: { intervalo_heartbeat_ms: 5000, limite_sem_heartbeat_ms: 15000 },
  pesagens_abertas: [pesagem()],
  liberacoes_caminhao: [],
  ultima_leitura_placa: null,
  dispositivos: {
    balanca: {
      modo: "SIMULADO",
      comunicacao: "OK",
      motivo_falha: null,
      comunicacao_em: T0,
      ultima_leitura: { peso_kg: "15000.000", lida_em: T0 },
      avaliacao_peso: null,
    },
    cancelas: [
      {
        cancela: "ENTRADA",
        modo: "SIMULADO",
        estado: "FECHADA",
        estado_em: T0,
        ultimo_comando: null,
      },
      {
        cancela: "SAIDA",
        modo: "SIMULADO",
        estado: "FECHADA",
        estado_em: T0,
        ultimo_comando: null,
      },
    ],
    posicao: { modo: "SIMULADO", resultado: "CONFIRMADA", capturada_em: T0, analisada_em: T0 },
    identificacao: { modo: "SIMULADO", resultado: "OK", analisada_em: T0 },
  },
  ...campos,
});
