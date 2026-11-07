import { afterEach, describe, expect, it, vi } from "vitest";
import type { Lista } from "../tipos/comum";
import type { Veiculo } from "../tipos/cadastros";
import { agendamentos, faixasHorario } from "./agendamentos";
import { veiculos } from "./cadastros";
import { comQuery } from "./cliente-api";

function capturarFetch(corpo: unknown) {
  const f = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(corpo), { status: 200 }));
  vi.stubGlobal("fetch", f);
  return f;
}

afterEach(() => vi.unstubAllGlobals());

describe("comQuery", () => {
  it("omite parâmetros ausentes e codifica valores", () => {
    expect(comQuery("/veiculos", { ativo: true, placa: "ABC 1D23", pagina: undefined })).toBe(
      "/veiculos?ativo=true&placa=ABC+1D23",
    );
    expect(comQuery("/veiculos", {})).toBe("/veiculos");
  });
});

describe("rotas das specs 007 e 008", () => {
  it("lista veículos com filtros e paginação e devolve a lista tipada", async () => {
    const lista: Lista<Veiculo> = { itens: [], total: 0, pagina: 2, tamanho_pagina: 20 };
    const f = capturarFetch(lista);
    await expect(veiculos.listar({ ativo: true, pagina: 2, tamanho_pagina: 20 })).resolves.toEqual(
      lista,
    );
    expect(f.mock.calls[0]?.[0]).toBe("/api/veiculos?ativo=true&pagina=2&tamanho_pagina=20");
  });

  it("cancela agendamento com POST e motivo", async () => {
    const f = capturarFetch({});
    await agendamentos.cancelar(7, { motivo: "Motorista desistiu." });
    expect(f.mock.calls[0]?.[0]).toBe("/api/agendamentos/7/cancelar");
    expect(f.mock.calls[0]?.[1]?.body).toBe('{"motivo":"Motorista desistiu."}');
  });

  it("consulta a disponibilidade do dia", async () => {
    const f = capturarFetch({ data: "2026-11-08", itens: [] });
    await faixasHorario.disponibilidade("2026-11-08");
    expect(f.mock.calls[0]?.[0]).toBe("/api/faixas-horario/disponibilidade?data=2026-11-08");
  });
});
