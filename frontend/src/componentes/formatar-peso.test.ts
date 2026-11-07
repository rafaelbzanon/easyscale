import { describe, expect, it } from "vitest";
import { formatarPeso } from "./formatar-peso";

describe("formatarPeso", () => {
  it("agrupa milhares e tira só os zeros à direita das casas", () => {
    expect(formatarPeso("15000.000")).toBe("15.000 kg");
    expect(formatarPeso("15000.500")).toBe("15.000,5 kg");
    expect(formatarPeso("15000.125")).toBe("15.000,125 kg");
    expect(formatarPeso("12")).toBe("12 kg");
  });

  it("nunca troca um valor por zero e mantém o sinal (RN-006)", () => {
    expect(formatarPeso("0.010")).toBe("0,01 kg");
    expect(formatarPeso("-6000.500")).toBe("−6.000,5 kg");
  });
});
