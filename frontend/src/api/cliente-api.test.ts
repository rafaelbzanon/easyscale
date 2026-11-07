import { afterEach, describe, expect, it, vi } from "vitest";
import type { ErroApi } from "../tipos/comum";
import { definirAoNaoAutenticado, ErroRequisicao, requisitar } from "./cliente-api";

function responder(status: number, corpo?: unknown) {
  const fetchSimulado = vi
    .fn<typeof fetch>()
    .mockResolvedValue(
      new Response(corpo === undefined ? null : JSON.stringify(corpo), { status }),
    );
  vi.stubGlobal("fetch", fetchSimulado);
  return fetchSimulado;
}

const erro = (codigo: string): ErroApi => ({ erro: { codigo, mensagem: "Texto.", campos: [] } });

async function capturar(promessa: Promise<unknown>): Promise<ErroRequisicao> {
  try {
    await promessa;
  } catch (e) {
    if (e instanceof ErroRequisicao) return e;
  }
  throw new Error("esperava ErroRequisicao");
}

afterEach(() => {
  vi.unstubAllGlobals();
  definirAoNaoAutenticado(() => undefined);
});

describe("CA-002: formato das requisições", () => {
  it.each(["POST", "PATCH", "DELETE"] as const)("%s sem corpo envia JSON {}", async (metodo) => {
    const fetchSimulado = responder(204);
    await requisitar(metodo, "/sessoes/atual");
    expect(fetchSimulado).toHaveBeenCalledWith("/api/sessoes/atual", {
      method: metodo,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  });

  it("GET usa o cookie e não envia corpo", async () => {
    const fetchSimulado = responder(200, { ok: true });
    await expect(requisitar("GET", "/operacao/estado")).resolves.toEqual({ ok: true });
    expect(fetchSimulado).toHaveBeenCalledWith("/api/operacao/estado", {
      method: "GET",
      credentials: "same-origin",
    });
  });
});

describe("CA-003: 401", () => {
  it("NAO_AUTENTICADO chama a ida ao login", async () => {
    const aoNaoAutenticado = vi.fn();
    definirAoNaoAutenticado(aoNaoAutenticado);
    responder(401, erro("NAO_AUTENTICADO"));
    const e = await capturar(requisitar("GET", "/sessoes/atual"));
    expect(e.erro?.codigo).toBe("NAO_AUTENTICADO");
    expect(aoNaoAutenticado).toHaveBeenCalledOnce();
  });

  it("CREDENCIAIS_INVALIDAS não redireciona", async () => {
    const aoNaoAutenticado = vi.fn();
    definirAoNaoAutenticado(aoNaoAutenticado);
    responder(401, erro("CREDENCIAIS_INVALIDAS"));
    const e = await capturar(requisitar("POST", "/sessoes", { login: "a", senha: "b" }));
    expect(e.erro?.codigo).toBe("CREDENCIAIS_INVALIDAS");
    expect(aoNaoAutenticado).not.toHaveBeenCalled();
  });
});

describe("CA-004: 403", () => {
  it("SEM_PERMISSAO vira erro com o código", async () => {
    responder(403, erro("SEM_PERMISSAO"));
    const e = await capturar(requisitar("GET", "/usuarios"));
    expect(e.status).toBe(403);
    expect(e.erro?.codigo).toBe("SEM_PERMISSAO");
  });
});

describe("CA-005: respostas sem o formato do contrato", () => {
  it("corpo de erro fora do formato dá erro nulo", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(new Response("<html>502</html>", { status: 502 })),
    );
    const e = await capturar(requisitar("GET", "/operacao/estado"));
    expect(e.status).toBe(502);
    expect(e.erro).toBeNull();
  });

  it("falha de rede dá status 0", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new TypeError("rede")));
    const e = await capturar(requisitar("POST", "/sessoes"));
    expect(e.status).toBe(0);
    expect(e.erro).toBeNull();
  });

  it("200 sem JSON não é dado como sucesso", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>().mockResolvedValue(new Response("", { status: 200 })),
    );
    const e = await capturar(requisitar("GET", "/operacao/estado"));
    expect(e.erro).toBeNull();
  });
});
