/** Data de hoje do navegador, `AAAA-MM-DD`. O dia do pátio é do backend (spec 019 Q-F4). */
export function hoje(): string {
  const d = new Date();
  const dois = (n: number) => String(n).padStart(2, "0");
  return `${String(d.getFullYear())}-${dois(d.getMonth() + 1)}-${dois(d.getDate())}`;
}

/** `2026-11-07` vira `07/11/2026`. */
export const formatarData = (iso: string) => iso.split("-").reverse().join("/");
