import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Rotas } from "../../rotas";
import { corposEnviados, erroApi, simularApi, type RotasSimuladas } from "../../simular-api";
import type { Lista } from "../../tipos/comum";
import type {
  CenariosSimuladores,
  ImagemDecisao,
  LeituraPlacaDetalhe,
} from "../../tipos/diagnostico";
import type { LeituraPlaca } from "../../tipos/operacao";
import { canal, CanalFalso } from "../operacao/canal-falso";
import { estadoOperacao, T0 } from "../operacao/dados-teste";

const leitura = (campos: Partial<LeituraPlaca> = {}): LeituraPlaca => ({
  id: 88,
  decisao: "NAO_AUTORIZADA",
  motivo: "CONFIANCA_BAIXA",
  placa_lida: "XYZ9A88",
  placa_normalizada: "XYZ9A88",
  confianca: "0.612",
  pesagem_id: null,
  agendamento_id: null,
  imagem_id: 501,
  capturada_em: T0,
  decidida_em: T0,
  ...campos,
});
const LISTA: Lista<LeituraPlaca> = {
  itens: [
    leitura(),
    leitura({
      id: 87,
      decisao: "AUTORIZADA",
      motivo: null,
      placa_normalizada: "ABC1D23",
      imagem_id: null,
    }),
  ],
  total: 2,
  pagina: 1,
  tamanho_pagina: 50,
};
const DETALHE: LeituraPlacaDetalhe = {
  ...leitura(),
  formato: "MERCOSUL",
  correcoes: [{ posicao: 5, lido: "O", corrigido: "0" }],
  origem: "camera-entrada",
  leituras: [
    {
      roi: { x: 10, y: 20, largura: 120, altura: 40 },
      textos: [
        { texto: "XYZ9A88", confianca: "0.612" },
        { texto: "XYZ9488", confianca: "0.201" },
      ],
    },
    { roi: { x: 300, y: 50, largura: 80, altura: 30 }, textos: [] },
  ],
};
const IMAGEM: ImagemDecisao = {
  id: 501,
  origem: "camera-entrada",
  capturada_em: T0,
  roi: null,
  excluida: false,
  excluida_por: null,
  excluida_por_nome: null,
  excluida_em: null,
  motivo_exclusao: null,
};
const CENARIOS: CenariosSimuladores = {
  balanca: { cenario: "ESTAVEL", peso_kg: "15000.000", amplitude_kg: null },
  cancelas: [
    { cancela: "ENTRADA", cenario: "CONFIRMADO" },
    { cancela: "SAIDA", cenario: "CONFIRMADO" },
  ],
  posicao: { cenario: "AUSENTE" },
  chegadas_na_fila: 0,
};

async function abrir(permissoes: string[], rotas: RotasSimuladas = {}) {
  const f = simularApi({
    "GET /api/sessoes/atual": [
      200,
      {
        usuario: { id: 1, nome: "Ana", login: "ana", perfil: "ADMINISTRADOR" },
        permissoes: ["CONSULTAR_OPERACAO", ...permissoes],
      },
    ],
    "GET /api/operacao/estado": [200, estadoOperacao()],
    "GET /api/dispositivos": [
      200,
      { gerado_em: T0, intervalo_imagem_ms: 1000, dispositivos: estadoOperacao().dispositivos },
    ],
    "GET /api/leituras-placa?pagina=1": [200, LISTA],
    "GET /api/leituras-placa/88": [200, DETALHE],
    "GET /api/imagens-decisao/501": [200, IMAGEM],
    "GET /api/imagens-decisao/501/conteudo": [200, "bytes"],
    "GET /api/cameras/identificacao/imagem-atual": [200, "bytes"],
    "GET /api/cameras/posicao/imagem-atual": [
      409,
      erroApi("CONFLITO", [{ campo: "camera", codigo: "SEM_IMAGEM" }]),
    ],
    "GET /api/simuladores": [404, erroApi("NAO_ENCONTRADO")],
    ...rotas,
  });
  render(
    <MemoryRouter initialEntries={["/diagnostico"]}>
      <Rotas />
    </MemoryRouter>,
  );
  await screen.findByRole("heading", { name: "Diagnóstico" });
  await vi.waitFor(() => canal());
  canal().abrir();
  await screen.findByText("Atualizada");
  return f;
}
const chamadas = (f: ReturnType<typeof simularApi>, url: string) =>
  f.mock.calls.filter(([u]) => u === url).length;

beforeEach(() => {
  CanalFalso.instancias = [];
  vi.stubGlobal("EventSource", CanalFalso);
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("spec 023: diagnóstico", () => {
  it("CA-001: seções seguem as permissões", async () => {
    await abrir(["CONSULTAR_IMAGENS_DECISAO"]);
    expect(screen.queryByRole("region", { name: "Câmeras" })).not.toBeInTheDocument();
    const u = userEvent.setup();
    await u.click(
      (await screen.findAllByRole("button", { name: "Ver detalhes" }))[0] as HTMLElement,
    );
    await screen.findByText("Leituras por ROI");
    expect(screen.queryByRole("button", { name: "Excluir imagem" })).not.toBeInTheDocument();
  });

  it("CA-001: sem CONSULTAR_IMAGENS_DECISAO não há detalhe", async () => {
    await abrir([]);
    await screen.findByText("ABC1D23");
    expect(screen.queryByRole("button", { name: "Ver detalhes" })).not.toBeInTheDocument();
  });

  it("CA-002 e CA-003: pede a imagem no intervalo, para quando desatualizada; SEM_IMAGEM avisa", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const f = await abrir(["CONSULTAR_IMAGENS_TEMPO_REAL"]);
    const url = "/api/cameras/identificacao/imagem-atual";
    await vi.waitFor(() => {
      expect(chamadas(f, url)).toBeGreaterThanOrEqual(1);
    });
    expect(await screen.findByText("Sem imagem desta câmera.")).toBeInTheDocument();
    const antes = chamadas(f, url);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(chamadas(f, url)).toBeGreaterThan(antes);
    canal().cair();
    const parado = chamadas(f, url);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(chamadas(f, url)).toBe(parado);
  });

  it("CA-004: lista na ordem do backend; filtro envia decisao=NAO_AUTORIZADA", async () => {
    const f = await abrir([], {
      "GET /api/leituras-placa?pagina=1&decisao=NAO_AUTORIZADA": [
        200,
        { ...LISTA, itens: [leitura()], total: 1 },
      ],
    });
    const placas = (await screen.findAllByText(/^(XYZ9A88|ABC1D23)$/)).map((e) => e.textContent);
    expect(placas).toEqual(["XYZ9A88", "ABC1D23"]);
    await userEvent.setup().click(screen.getByLabelText("Só não autorizadas"));
    await vi.waitFor(() => {
      expect(chamadas(f, "/api/leituras-placa?pagina=1&decisao=NAO_AUTORIZADA")).toBe(1);
    });
  });

  it("CA-005 e CA-006: detalhe com todas as ROIs, textos e correções, desenhadas sobre a imagem", async () => {
    await abrir(["CONSULTAR_IMAGENS_DECISAO"]);
    const u = userEvent.setup();
    await u.click(
      (await screen.findAllByRole("button", { name: "Ver detalhes" }))[0] as HTMLElement,
    );
    expect(await screen.findByText(/XYZ9A88 \(0.612\), XYZ9488 \(0.201\)/)).toBeInTheDocument();
    expect(screen.getByText(/nenhum texto/)).toBeInTheDocument();
    expect(screen.getByText("posição 5: O → 0")).toBeInTheDocument();
    const img = await screen.findByAltText("Imagem da leitura 88");
    Object.defineProperty(img, "naturalWidth", { value: 640 });
    Object.defineProperty(img, "naturalHeight", { value: 480 });
    fireEvent.load(img);
    const figura = img.closest("figure");
    if (!figura) throw new Error("figura ausente");
    const rois = figura.querySelectorAll("rect");
    expect(
      [...rois].map((r) => [
        r.getAttribute("data-roi"),
        r.getAttribute("x"),
        r.getAttribute("width"),
      ]),
    ).toEqual([
      ["1", "10", "120"],
      ["2", "300", "80"],
    ]);
    expect(figura.querySelector("svg")?.getAttribute("viewBox")).toBe("0 0 640 480");
  });

  it("CA-007: imagem excluída mostra quem, quando e o motivo", async () => {
    await abrir(["CONSULTAR_IMAGENS_DECISAO"], {
      "GET /api/imagens-decisao/501": [
        200,
        {
          ...IMAGEM,
          excluida: true,
          excluida_por: 1,
          excluida_por_nome: "Ana",
          excluida_em: T0,
          motivo_exclusao: "Pedido do titular",
        },
      ],
    });
    await userEvent
      .setup()
      .click((await screen.findAllByRole("button", { name: "Ver detalhes" }))[0] as HTMLElement);
    expect(
      await screen.findByText(/Imagem excluída por Ana em .*Motivo: Pedido do titular/),
    ).toBeInTheDocument();
  });

  it("CA-008: excluir envia o motivo só depois da confirmação", async () => {
    const f = await abrir(["CONSULTAR_IMAGENS_DECISAO", "EXCLUIR_IMAGENS_DECISAO"], {
      "POST /api/imagens-decisao/501/excluir": [200, { ...IMAGEM, excluida: true }],
    });
    const u = userEvent.setup();
    await u.click(
      (await screen.findAllByRole("button", { name: "Ver detalhes" }))[0] as HTMLElement,
    );
    await u.click(await screen.findByRole("button", { name: "Excluir imagem" }));
    expect(corposEnviados(f, "POST /api/imagens-decisao/501/excluir")).toEqual([]);
    await u.type(screen.getByLabelText("Motivo da exclusão"), "Pedido do titular");
    await u.click(screen.getByRole("button", { name: "Confirmar exclusão" }));
    await vi.waitFor(() => {
      expect(corposEnviados(f, "POST /api/imagens-decisao/501/excluir")).toEqual([
        { motivo: "Pedido do titular" },
      ]);
    });
  });

  it("CA-009: 404 esconde os simuladores", async () => {
    await abrir(["CONTROLAR_SIMULADORES"]);
    await screen.findByText("ABC1D23");
    expect(screen.queryByRole("region", { name: "Simuladores" })).not.toBeInTheDocument();
  });

  it("CA-009 e CA-010: troca da balança com nulos e chegada simulada", async () => {
    const f = await abrir(["CONTROLAR_SIMULADORES"], {
      "GET /api/simuladores": [200, CENARIOS],
      "POST /api/simuladores/balanca": [
        200,
        { ...CENARIOS, balanca: { cenario: "SEM_RESPOSTA", peso_kg: null, amplitude_kg: null } },
      ],
      "POST /api/simuladores/chegadas": [202, { ...CENARIOS, chegadas_na_fila: 1 }],
    });
    const sim = await screen.findByRole("region", { name: "Simuladores" });
    const u = userEvent.setup();
    await u.selectOptions(within(sim).getByLabelText("Balança"), "SEM_RESPOSTA");
    expect(within(sim).queryByLabelText("Peso (kg)")).not.toBeInTheDocument();
    await u.click(within(sim).getByRole("button", { name: "Aplicar à balança" }));
    await u.click(within(sim).getByRole("button", { name: "Simular chegada" }));
    await u.type(within(sim).getByLabelText("Placa da chegada"), "ABC1D23");
    await u.type(within(sim).getByLabelText("Confiança (0 a 1)"), "0.950");
    await u.click(within(sim).getByRole("button", { name: "Simular chegada" }));
    await within(sim).findByText("Na fila: 1");
    expect(corposEnviados(f, "POST /api/simuladores/balanca")).toEqual([
      { cenario: "SEM_RESPOSTA", peso_kg: null, amplitude_kg: null },
    ]);
    expect(corposEnviados(f, "POST /api/simuladores/chegadas")).toEqual([
      { textos: [] },
      { textos: [{ texto: "ABC1D23", confianca: "0.950" }] },
    ]);
  });
});
