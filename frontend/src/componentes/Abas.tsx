import { Link } from "react-router";

/** Abas como links: a aba ativa fica no endereço. Sem azul: azul é ação disponível. */
export function Abas({
  rotulo,
  itens,
}: {
  rotulo: string;
  itens: { rotulo: string; para: string; ativa: boolean }[];
}) {
  return (
    <nav aria-label={rotulo} className="mb-6 flex flex-wrap gap-x-6 border-b border-fio">
      {itens.map((i) => (
        <Link
          key={i.para}
          to={i.para}
          aria-current={i.ativa ? "page" : undefined}
          className={`-mb-px border-b-4 py-2 font-semibold ${i.ativa ? "border-tinta" : "border-transparent text-suave hover:text-tinta"}`}
        >
          {i.rotulo}
        </Link>
      ))}
    </nav>
  );
}
