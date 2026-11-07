import { useEffect, useState } from "react";

/**
 * Carrega dados de uma chamada. `chave` resume as entradas de `carregar`: quando muda, recarrega
 * e `carregando` volta a ser verdadeiro, sem mostrar o resultado da chave anterior.
 */
export function useCarga<T>(carregar: () => Promise<T>, chave: string) {
  const [tentativa, setTentativa] = useState(0);
  const [resultado, setResultado] = useState<{ chave: string; dados?: T; erro?: unknown } | null>(
    null,
  );
  const chaveCompleta = `${chave}#${String(tentativa)}`;

  useEffect(() => {
    let ativo = true;
    carregar().then(
      (dados) => {
        if (ativo) setResultado({ chave: chaveCompleta, dados });
      },
      (erro: unknown) => {
        if (ativo) setResultado({ chave: chaveCompleta, erro });
      },
    );
    return () => {
      ativo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `chaveCompleta` resume as entradas de `carregar`
  }, [chaveCompleta]);

  const atual = resultado?.chave === chaveCompleta ? resultado : null;
  return {
    carregando: atual === null,
    dados: atual?.dados,
    erro: atual?.erro,
    recarregar: () => {
      setTentativa((t) => t + 1);
    },
  };
}
