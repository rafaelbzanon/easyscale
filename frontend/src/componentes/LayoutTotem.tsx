import { Outlet } from "react-router";
import { Cabecalho } from "./Cabecalho";

/** Casca do totem: sem sessão, texto e alvos de toque grandes (spec 016 §6.3, §8.4). */
export function LayoutTotem() {
  return (
    <div className="flex min-h-dvh flex-col text-xl">
      <Cabecalho titulo="Agendamento do motorista" grande />
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 px-4 py-8 [&_button]:min-h-16 [&_button]:px-6 [&_button]:text-xl">
        <Outlet />
      </main>
    </div>
  );
}
