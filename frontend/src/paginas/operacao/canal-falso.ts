// Só para testes: EventSource falso, controlado pelo teste (o jsdom não tem EventSource).
import { act } from "@testing-library/react";

export class CanalFalso {
  static readonly CLOSED = 2;
  static instancias: CanalFalso[] = [];
  readyState = 0;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  private ouvintes = new Map<string, ((m: { data: string }) => void)[]>();
  constructor(readonly url: string) {
    CanalFalso.instancias.push(this);
  }
  addEventListener(tipo: string, f: (m: { data: string }) => void) {
    this.ouvintes.set(tipo, [...(this.ouvintes.get(tipo) ?? []), f]);
  }
  close() {
    this.readyState = 2;
  }
  abrir() {
    act(() => {
      this.readyState = 1;
      this.onopen?.();
    });
  }
  emitir(tipo: string, dados: unknown) {
    act(() => {
      for (const f of this.ouvintes.get(tipo) ?? []) f({ data: JSON.stringify(dados) });
    });
  }
  cair() {
    act(() => {
      this.readyState = 0;
      this.onerror?.();
    });
  }
}
export const canal = () => {
  const c = CanalFalso.instancias.at(-1);
  if (!c) throw new Error("canal não aberto");
  return c;
};
