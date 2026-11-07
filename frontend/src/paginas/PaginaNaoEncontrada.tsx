import { Link } from "react-router";

export function PaginaNaoEncontrada() {
  return (
    <section className="max-w-prose">
      <h1 className="mb-2 text-2xl font-bold">Página não encontrada</h1>
      <Link to="/" className="font-semibold text-azul underline">
        Voltar ao início
      </Link>
    </section>
  );
}
