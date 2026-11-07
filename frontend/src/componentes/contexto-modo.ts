import { createContext, use, useEffect } from "react";

/** A tela operacional informa ao LayoutBase os `dispositivos` recebidos pelo canal (spec 022 CA-012). */
export const ContextoModo = createContext<(dispositivos: unknown) => void>(() => undefined);

export function useInformarDispositivos(dispositivos: unknown) {
  const informar = use(ContextoModo);
  useEffect(() => {
    if (dispositivos !== undefined) informar(dispositivos);
  }, [informar, dispositivos]);
}
