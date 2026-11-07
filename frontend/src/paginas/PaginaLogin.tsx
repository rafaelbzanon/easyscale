import { useState, type SyntheticEvent } from "react";
import { useNavigate } from "react-router";
import { ErroRequisicao } from "../api/cliente-api";
import { entrar } from "../api/sessao";
import { Botao } from "../componentes/Botao";
import { Cabecalho } from "../componentes/Cabecalho";
import { Campo } from "../componentes/Campo";
import { MensagemErro } from "../componentes/MensagemErro";

// Spec 017 §4: mensagens próprias do login; o resto usa a mensagem comum.
function mensagemLogin(erro: unknown): string | null {
  if (!(erro instanceof ErroRequisicao)) return null;
  if (erro.erro?.codigo === "CREDENCIAIS_INVALIDAS") return "Login ou senha incorretos.";
  if (erro.erro?.codigo === "LOGIN_BLOQUEADO") {
    return "Login bloqueado por excesso de tentativas. Tente de novo mais tarde.";
  }
  return null;
}

export function PaginaLogin() {
  const navegar = useNavigate();
  const [login, setLogin] = useState("");
  // A senha só vive aqui, e é limpa depois de cada resposta (ADR-0004).
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<unknown>(null);

  const enviar = (evento: SyntheticEvent) => {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    entrar({ login, senha }).then(
      () => void navegar("/", { replace: true }),
      (e: unknown) => {
        setErro(e);
        setSenha("");
        setEnviando(false);
      },
    );
  };

  return (
    <div className="min-h-dvh">
      <Cabecalho />
      <main className="mx-auto max-w-sm px-4 py-10">
        <h1 className="mb-6 text-2xl font-bold">Entrar</h1>
        <form onSubmit={enviar} className="flex flex-col gap-4">
          <Campo
            rotulo="Login"
            name="login"
            autoComplete="username"
            required
            value={login}
            onChange={(e) => {
              setLogin(e.target.value);
            }}
          />
          <Campo
            rotulo="Senha"
            name="senha"
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => {
              setSenha(e.target.value);
            }}
          />
          {erro !== null && <MensagemErro erro={erro} texto={mensagemLogin(erro)} />}
          <Botao type="submit" variante="acao" disabled={enviando} className="self-start">
            {enviando ? "Entrando…" : "Entrar"}
          </Botao>
        </form>
      </main>
    </div>
  );
}
