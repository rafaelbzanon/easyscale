import type { ModoDispositivo } from "../tipos/operacao";
import { SimboloEstado } from "./SimboloEstado";

export type ResumoModo =
  { tipo: "SIMULADO" } | { tipo: "REAL"; reais: string[] } | { tipo: "DESCONHECIDO" };

const DESCONHECIDO: ResumoModo = { tipo: "DESCONHECIDO" };

function modoDe(valor: unknown): ModoDispositivo | null {
  if (typeof valor !== "object" || valor === null || !("modo" in valor)) return null;
  return valor.modo === "SIMULADO" || valor.modo === "REAL" ? valor.modo : null;
}

function nomeCancela(valor: unknown): string | null {
  if (typeof valor !== "object" || valor === null || !("cancela" in valor)) return null;
  if (valor.cancela === "ENTRADA") return "cancela de entrada";
  if (valor.cancela === "SAIDA") return "cancela de saída";
  return null;
}

/**
 * Resume os quatro `modo` de `dispositivos` (spec 009 §5.4). Recebe a resposta crua, porque é
 * fronteira: qualquer campo ausente ou inesperado vira DESCONHECIDO, nunca SIMULADO (spec 016 §6.4).
 */
export function resumirModo(estado: unknown): ResumoModo {
  if (typeof estado !== "object" || estado === null || !("dispositivos" in estado)) {
    return DESCONHECIDO;
  }
  const d = estado.dispositivos;
  if (typeof d !== "object" || d === null) return DESCONHECIDO;
  const cancelas: unknown[] = "cancelas" in d && Array.isArray(d.cancelas) ? d.cancelas : [];
  if (cancelas.length !== 2) return DESCONHECIDO;

  const itens: [string | null, unknown][] = [
    ["balança", "balanca" in d ? d.balanca : null],
    ...cancelas.map((c): [string | null, unknown] => [nomeCancela(c), c]),
    ["câmera de posição", "posicao" in d ? d.posicao : null],
    ["identificação de placa", "identificacao" in d ? d.identificacao : null],
  ];
  const reais: string[] = [];
  for (const [nome, valor] of itens) {
    const modo = modoDe(valor);
    if (nome === null || modo === null) return DESCONHECIDO;
    if (modo === "REAL") reais.push(nome);
  }
  return reais.length > 0 ? { tipo: "REAL", reais } : { tipo: "SIMULADO" };
}

export function PlacaModo({ estado }: { estado: unknown }) {
  const resumo = resumirModo(estado);
  const base = "inline-flex items-center gap-2 border-2 px-3 py-1 text-sm";
  if (resumo.tipo === "REAL") {
    return (
      <p className={`${base} border-vermelho bg-vermelho text-claro`}>
        <SimboloEstado tipo="atencao" />
        <strong className="font-bold tracking-wide">REAL</strong>
        <span>· equipamento físico: {resumo.reais.join(", ")}</span>
      </p>
    );
  }
  if (resumo.tipo === "SIMULADO") {
    return (
      <p className={`${base} border-azul bg-claro text-tinta`}>
        <SimboloEstado tipo="informacao" />
        <strong className="font-bold tracking-wide">SIMULADO</strong>
        <span>· nenhum equipamento físico</span>
      </p>
    );
  }
  return (
    <p className={`${base} border-tinta bg-amarelo text-tinta`}>
      <SimboloEstado tipo="atencao" />
      <strong className="font-bold tracking-wide">MODO DESCONHECIDO</strong>
    </p>
  );
}
