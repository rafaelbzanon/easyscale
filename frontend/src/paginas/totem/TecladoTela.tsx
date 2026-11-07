import { Botao } from "../../componentes/Botao";

const ALFANUMERICO = ["1234567890", "QWERTYUIOP", "ASDFGHJKL-", "ZXCVBNM"].map((l) => l.split(""));
const NUMERICO = ["123", "456", "789"].map((l) => l.split(""));

/** Teclado na tela para o totem sem teclado físico. Os botões não tiram o foco do campo (leitor de código). */
export function TecladoTela({
  tipo,
  aoDigitar,
  aoApagar,
}: {
  tipo: "numerico" | "alfanumerico";
  aoDigitar: (c: string) => void;
  aoApagar: () => void;
}) {
  const linhas = tipo === "numerico" ? NUMERICO : ALFANUMERICO;
  const props = {
    onMouseDown: (e: { preventDefault: () => void }) => {
      e.preventDefault();
    },
  };
  const tecla = (c: string) => (
    <Botao
      key={c}
      className="flex-1 justify-center"
      {...props}
      onClick={() => {
        aoDigitar(c);
      }}
    >
      {c}
    </Botao>
  );
  const apagar = (
    <Botao
      className={tipo === "numerico" ? "flex-1 justify-center" : "flex-[2] justify-center"}
      {...props}
      onClick={aoApagar}
    >
      Apagar
    </Botao>
  );
  return (
    <div role="group" aria-label="Teclado" className="flex flex-col gap-2">
      {linhas.map((linha) => (
        <div key={linha.join("")} className="flex gap-2">
          {linha.map(tecla)}
          {tipo === "alfanumerico" && linha[0] === "Z" && apagar}
        </div>
      ))}
      {tipo === "numerico" && (
        <div className="flex gap-2">
          {apagar}
          {tecla("0")}
        </div>
      )}
    </div>
  );
}
