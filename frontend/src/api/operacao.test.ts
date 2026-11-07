import { afterEach, describe, expect, it, vi } from "vitest";
import type { AcaoManual } from "../tipos/operacao";
import { executarAcao } from "./operacao";

afterEach(() => vi.unstubAllGlobals());

// Spec 009 §4.2: cada valor de acoes_disponiveis vai para a sua rota, com versao e motivo.
describe("ações sobre a pesagem", () => {
  it.each<[AcaoManual, string]>([
    ["TENTAR_NOVAMENTE", "tentar-novamente"],
    ["CONFIRMAR_POSICAO_MANUAL", "confirmar-posicao"],
    ["CONFIRMAR_BALANCA_VAZIA_MANUAL", "confirmar-balanca-vazia"],
    ["LIBERAR_RETORNO_MANUAL", "liberar-retorno"],
    ["ACEITAR_PESO_FINAL", "aceitar-peso-final"],
    ["CANCELAR", "cancelar"],
  ])("%s usa /pesagens/{id}/%s", async (acao, rota) => {
    const f = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", f);
    await executarAcao(12, acao, { versao: 7, motivo: "Conferido no local." });
    expect(f.mock.calls[0]?.[0]).toBe(`/api/pesagens/12/${rota}`);
    expect(f.mock.calls[0]?.[1]?.body).toBe('{"versao":7,"motivo":"Conferido no local."}');
  });
});
