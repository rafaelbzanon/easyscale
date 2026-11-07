import { act, cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Rotas } from "../../rotas";
import { corposEnviados, erroApi, simularApi, type RotasSimuladas } from "../../simular-api";
import type { EstadoOperacao } from "../../tipos/operacao";
import type { UsuarioAtual } from "../../tipos/sessao";
import { canal, CanalFalso } from "./canal-falso";
import { depois, estadoOperacao, liberacao, pesagem } from "./dados-teste";

const sessao = (permissoes: string[]): UsuarioAtual => ({
  usuario: { id: 1, nome: "Ana Lima", login: "ana", perfil: "ADMINISTRADOR" },
  permissoes: ["CONSULTAR_OPERACAO", ...permissoes],
});

async function abrir(
  estado: EstadoOperacao,
  permissoes: string[] = [],
  rotas: RotasSimuladas = {},
) {
  const f = simularApi({
    "GET /api/sessoes/atual": [200, sessao(permissoes)],
    "GET /api/operacao/estado": [200, estado],
    ...rotas,
  });
  render(
    <MemoryRouter initialEntries={["/operacao"]}>
      <Rotas />
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: "Operação" });
  // O título pode aparecer antes do efeito que cria o canal.
  await vi.waitFor(() => canal());
  return f;
}
const sincronizar = async () => {
  canal().abrir();
  await screen.findByText("Atualizada");
};

beforeEach(() => {
  CanalFalso.instancias = [];
  vi.stubGlobal("EventSource", CanalFalso);
});
afterEach(() => {
  // Desmonta antes de tirar o EventSource falso, para nenhum efeito pendente criar um canal.
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const INTERVENCAO = pesagem({
  situacao: "AGUARDANDO_INTERVENCAO",
  situacao_anterior: "POSICIONADA_INICIAL",
  motivo_intervencao: "TEMPO_ESGOTADO",
  acoes_disponiveis: ["TENTAR_NOVAMENTE", "CONFIRMAR_POSICAO_MANUAL", "CANCELAR"],
});

describe("spec 022: tela operacional", () => {
  it("CA-001: abre o canal e só mostra e libera depois do estado", async () => {
    await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), ["TENTAR_NOVAMENTE"]);
    expect(canal().url).toBe("/api/operacao/eventos");
    expect(screen.getByText("Sincronizando…")).toBeInTheDocument();
    expect(screen.queryByText("ABC1D23")).not.toBeInTheDocument();
    await sincronizar();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeEnabled();
  });

  it("CA-002: evento com versão menor é ignorado; maior substitui", async () => {
    await abrir(estadoOperacao());
    await sincronizar();
    canal().emitir("pesagem", pesagem({ versao: 2, situacao: "CANCELADA" }));
    expect(screen.getByText("Na balança (pesagem inicial)")).toBeInTheDocument();
    canal().emitir("pesagem", pesagem({ versao: 4, situacao: "PESO_INICIAL_OK" }));
    expect(screen.getByText("Peso inicial registrado")).toBeInTheDocument();
  });

  it("CA-004: sem mensagem além do limite, avisa e bloqueia; heartbeat sozinho não libera após queda", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), ["TENTAR_NOVAMENTE"]);
    await sincronizar();
    act(() => {
      vi.advanceTimersByTime(16000);
    });
    expect(screen.getAllByText(/Tela desatualizada/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
    canal().cair();
    canal().emitir("heartbeat", { enviado_em: depois(20) });
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
  });

  it("CA-005: canal caído bloqueia; ao reabrir, busca o estado e libera", async () => {
    const f = await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), [
      "TENTAR_NOVAMENTE",
    ]);
    await sincronizar();
    const antes = f.mock.calls.length;
    canal().cair();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
    await sincronizar();
    expect(f.mock.calls.length).toBeGreaterThan(antes);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeEnabled();
  });

  it("CA-006 e CA-011: falhas com palavra e forma; leitura separada do peso aceito", async () => {
    const e = estadoOperacao();
    e.dispositivos.balanca = {
      ...e.dispositivos.balanca,
      comunicacao: "FALHA",
      motivo_falha: "SEM_RESPOSTA",
    };
    e.dispositivos.cancelas = [
      {
        ...e.dispositivos.cancelas[0],
        estado: "DESCONHECIDO",
        ultimo_comando: {
          comando: "FECHAR",
          resultado: "SEM_CONFIRMACAO",
          tentativas: 2,
          concluido_em: depois(1),
          pesagem_id: 12,
        },
      },
      e.dispositivos.cancelas[1],
    ];
    await abrir(e);
    await sincronizar();
    const balanca = screen.getByRole("region", { name: "Balança" });
    expect(within(balanca).getByText("FALHA: sem resposta")).toBeInTheDocument();
    expect(within(balanca).getByText(/Leitura, não é peso aceito/)).toBeInTheDocument();
    const cancelas = screen.getByRole("region", { name: "Cancelas" });
    expect(within(cancelas).getByText("DESCONHECIDO")).toBeInTheDocument();
    expect(
      within(cancelas).getByText("Fechar: SEM CONFIRMAÇÃO (2 tentativas)"),
    ).toBeInTheDocument();
    expect(within(cancelas).getAllByText(/^(ABERTA|FECHADA)$/)).toHaveLength(1);
  });

  it("CA-007: só ações disponíveis e permitidas", async () => {
    await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), ["TENTAR_NOVAMENTE"]);
    await sincronizar();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar posição" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Liberar retorno" })).not.toBeInTheDocument();
  });

  it("CA-008: envia versão e motivo; sem motivo não envia", async () => {
    const f = await abrir(
      estadoOperacao({ pesagens_abertas: [INTERVENCAO] }),
      ["TENTAR_NOVAMENTE"],
      {
        "POST /api/pesagens/12/tentar-novamente": [200, pesagem({ versao: 4 })],
      },
    );
    await sincronizar();
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "Tentar novamente" }));
    const confirmar = screen.getByRole("button", { name: "Confirmar: tentar novamente" });
    expect(confirmar).toBeDisabled();
    await u.type(screen.getByLabelText("Motivo"), "Balança voltou.");
    await u.click(confirmar);
    expect(await screen.findByRole("status")).toHaveTextContent("Pedido aceito.");
    expect(corposEnviados(f, "POST /api/pesagens/12/tentar-novamente")).toEqual([
      { versao: 3, motivo: "Balança voltou." },
    ]);
    expect(screen.getByText("Na balança (pesagem inicial)")).toBeInTheDocument();
  });

  it("CA-009: versão desatualizada mostra a mensagem e não muda a pesagem", async () => {
    await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), ["INTERVIR_OPERACAO"], {
      "POST /api/pesagens/12/cancelar": [
        409,
        erroApi("CONFLITO", [{ campo: "versao", codigo: "VERSAO_DESATUALIZADA" }]),
      ],
    });
    await sincronizar();
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "Cancelar pesagem" }));
    await u.type(screen.getByLabelText("Motivo"), "Desistência.");
    await u.click(screen.getByRole("button", { name: "Confirmar: cancelar pesagem" }));
    expect(
      await screen.findByText(/A pesagem mudou desde que você abriu a ação/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Aguardando intervenção: Tempo esgotado/)).toBeInTheDocument();
  });

  it("CA-010: liberar caminhão com a permissão, em PENDENTE, envia o motivo", async () => {
    const f = await abrir(
      estadoOperacao({ liberacoes_caminhao: [liberacao()] }),
      ["LIBERAR_CAMINHAO_CANCELADO"],
      {
        "POST /api/pesagens/40/liberar-caminhao": [200, pesagem({ id: 40, situacao: "CANCELADA" })],
      },
    );
    await sincronizar();
    const u = userEvent.setup();
    await u.click(screen.getByRole("button", { name: "Liberar caminhão" }));
    await u.type(screen.getByLabelText("Motivo"), "Caminhão vazio, pode sair.");
    await u.click(screen.getByRole("button", { name: "Confirmar: liberar caminhão" }));
    await screen.findByRole("status");
    expect(corposEnviados(f, "POST /api/pesagens/40/liberar-caminhao")).toEqual([
      { motivo: "Caminhão vazio, pode sair." },
    ]);
  });

  it("CA-010: sem a permissão ou com liberação em curso, não há botão", async () => {
    await abrir(estadoOperacao({ liberacoes_caminhao: [liberacao({ etapa: "ABRINDO_SAIDA" })] }), [
      "LIBERAR_CAMINHAO_CANCELADO",
    ]);
    await sincronizar();
    expect(screen.queryByRole("button", { name: "Liberar caminhão" })).not.toBeInTheDocument();
  });

  it("CA-012: a placa de modo segue os dispositivos do canal", async () => {
    await abrir(estadoOperacao());
    await sincronizar();
    expect(await screen.findByText("SIMULADO")).toBeInTheDocument();
    const b = estadoOperacao().dispositivos.balanca;
    canal().emitir("balanca", { ...b, modo: "REAL", comunicacao_em: depois(3) });
    expect(await screen.findByText("REAL")).toBeInTheDocument();
  });

  it("CA-012: com a tela desatualizada, a placa mostra MODO DESCONHECIDO até o GET", async () => {
    await abrir(estadoOperacao());
    await sincronizar();
    expect(await screen.findByText("SIMULADO")).toBeInTheDocument();
    act(() => {
      canal().readyState = CanalFalso.CLOSED;
      canal().onerror?.();
    });
    expect(await screen.findByText("MODO DESCONHECIDO")).toBeInTheDocument();
    await sincronizar();
    expect(await screen.findByText("SIMULADO")).toBeInTheDocument();
  });
});

describe("spec 022 CA-005: canal fechado ou pendurado", () => {
  it("reabre o canal sozinho depois do limite sem mensagem", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await abrir(estadoOperacao());
    await sincronizar();
    const antes = CanalFalso.instancias.length;
    act(() => {
      canal().readyState = CanalFalso.CLOSED;
      canal().onerror?.();
    });
    expect(screen.getByRole("button", { name: "Reconectar" })).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(16000);
    });
    expect(CanalFalso.instancias.length).toBeGreaterThan(antes);
    await sincronizar();
  });
});

describe("spec 022 CA-005: conexão pendurada", () => {
  it("sem mensagem além do limite, fecha e reabre o canal e só libera após o GET", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    await abrir(estadoOperacao({ pesagens_abertas: [INTERVENCAO] }), ["TENTAR_NOVAMENTE"]);
    await sincronizar();
    const primeiro = canal();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(16000);
    });
    expect(primeiro.readyState).toBe(CanalFalso.CLOSED);
    expect(canal()).not.toBe(primeiro);
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeDisabled();
    await sincronizar();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeEnabled();
  });
});
