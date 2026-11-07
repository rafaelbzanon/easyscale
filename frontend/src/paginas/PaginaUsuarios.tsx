import { useEffect, useState, type SyntheticEvent } from "react";
import { ErroRequisicao } from "../api/cliente-api";
import { listarPerfis, usuarios } from "../api/sessao";
import { Botao } from "../componentes/Botao";
import { Campo, CLASSE_ENTRADA } from "../componentes/Campo";
import { MensagemErro } from "../componentes/MensagemErro";
import { nomePerfil } from "../componentes/nome-perfil";
import type { Lista } from "../tipos/comum";
import type { ListaPerfis, Usuario } from "../tipos/sessao";

const codigosCampo = (erro: unknown, campo: string) =>
  erro instanceof ErroRequisicao
    ? (erro.erro?.campos.filter((c) => c.campo === campo).map((c) => c.codigo) ?? [])
    : [];

/** Spec 017 §3.3. Só o administrador tem GERENCIAR_USUARIOS; o backend decide (403). */
export function PaginaUsuarios() {
  const [pagina, setPagina] = useState(1);
  const [lista, setLista] = useState<Lista<Usuario> | null>(null);
  const [erro, setErro] = useState<unknown>(null);
  const [recarga, setRecarga] = useState(0);
  const recarregar = () => {
    setRecarga((r) => r + 1);
  };

  useEffect(() => {
    let ativo = true;
    usuarios.listar({ pagina }).then(
      (l) => {
        if (ativo) {
          setLista(l);
          setErro(null);
        }
      },
      (e: unknown) => {
        if (ativo) {
          setLista(null);
          setErro(e);
        }
      },
    );
    return () => {
      ativo = false;
    };
  }, [pagina, recarga]);

  if (erro !== null) return <MensagemErro erro={erro} aoTentarNovamente={recarregar} />;
  if (!lista) return <p className="text-suave">Carregando…</p>;

  const paginas = Math.max(1, Math.ceil(lista.total / lista.tamanho_pagina));
  return (
    <div className="flex flex-col gap-8">
      <h1 className="text-2xl font-bold">Usuários</h1>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[40rem] border-collapse text-left">
          <thead>
            <tr className="border-b border-fio text-sm text-suave">
              <th className="py-2 pr-4 font-semibold">Nome</th>
              <th className="py-2 pr-4 font-semibold">Login</th>
              <th className="py-2 pr-4 font-semibold">Perfil</th>
              <th className="py-2 pr-4 font-semibold">Situação</th>
              <th className="py-2 font-semibold">Ações</th>
            </tr>
          </thead>
          <tbody>
            {lista.itens.map((u) => (
              <LinhaUsuario key={u.id} usuario={u} aoMudar={recarregar} />
            ))}
          </tbody>
        </table>
      </div>
      {paginas > 1 && (
        <div className="flex items-center gap-3 text-sm">
          <Botao
            disabled={pagina <= 1}
            onClick={() => {
              setPagina(pagina - 1);
            }}
          >
            Anterior
          </Botao>
          <span>
            Página {pagina} de {paginas} · {lista.total} usuários
          </span>
          <Botao
            disabled={pagina >= paginas}
            onClick={() => {
              setPagina(pagina + 1);
            }}
          >
            Próxima
          </Botao>
        </div>
      )}
      <FormNovoUsuario aoCriar={recarregar} />
    </div>
  );
}

function LinhaUsuario({ usuario, aoMudar }: { usuario: Usuario; aoMudar: () => void }) {
  const [modo, setModo] = useState<"normal" | "confirmar" | "senha">("normal");
  const [novaSenha, setNovaSenha] = useState("");
  const [erro, setErro] = useState<unknown>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const executar = (pedido: Promise<unknown>, depois: () => void) => {
    setEnviando(true);
    setErro(null);
    setAviso(null);
    pedido.then(
      () => {
        setEnviando(false);
        setModo("normal");
        depois();
      },
      (e: unknown) => {
        setEnviando(false);
        setErro(e);
        if (modo === "confirmar") setModo("normal");
      },
    );
  };
  const alterarAtivo = (ativo: boolean) => {
    executar(usuarios.alterar(usuario.id, { ativo }), aoMudar);
  };
  const redefinir = (evento: SyntheticEvent) => {
    evento.preventDefault();
    executar(usuarios.redefinirSenha(usuario.id, { nova_senha: novaSenha }), () => {
      setAviso("Senha redefinida. As sessões desse usuário foram encerradas.");
    });
    setNovaSenha("");
  };
  // 409 PROPRIO_USUARIO (spec 012 §6.5); o contrato não fixa o nome do campo.
  const proprio =
    erro instanceof ErroRequisicao &&
    (erro.erro?.campos.some((c) => c.codigo === "PROPRIO_USUARIO") ?? false);

  return (
    <>
      <tr className="border-b border-fio align-top">
        <td className="py-3 pr-4">{usuario.nome}</td>
        <td className="py-3 pr-4 font-mono">{usuario.login}</td>
        <td className="py-3 pr-4">{nomePerfil(usuario.perfil)}</td>
        <td className="py-3 pr-4">{usuario.ativo ? "Ativo" : "Inativo"}</td>
        <td className="py-3">
          <div className="flex flex-wrap gap-2">
            {modo === "confirmar" ? (
              <>
                <Botao
                  variante="acao"
                  disabled={enviando}
                  onClick={() => {
                    alterarAtivo(false);
                  }}
                >
                  Confirmar desativação
                </Botao>
                <Botao
                  onClick={() => {
                    setModo("normal");
                  }}
                >
                  Cancelar
                </Botao>
              </>
            ) : usuario.ativo ? (
              <Botao
                onClick={() => {
                  setModo("confirmar");
                }}
              >
                Desativar
              </Botao>
            ) : (
              <Botao
                disabled={enviando}
                onClick={() => {
                  alterarAtivo(true);
                }}
              >
                Reativar
              </Botao>
            )}
            <Botao
              onClick={() => {
                setModo(modo === "senha" ? "normal" : "senha");
              }}
            >
              Redefinir senha
            </Botao>
          </div>
        </td>
      </tr>
      {(modo === "confirmar" || modo === "senha" || erro !== null || aviso) && (
        <tr className="border-b border-fio">
          <td colSpan={5} className="pb-3">
            {modo === "confirmar" && (
              <p className="text-sm">
                Desativar encerra na hora todas as sessões de {usuario.nome}.
              </p>
            )}
            {modo === "senha" && (
              <form onSubmit={redefinir} className="flex flex-wrap items-end gap-2">
                <Campo
                  rotulo={`Nova senha de ${usuario.nome}`}
                  type="password"
                  autoComplete="new-password"
                  required
                  value={novaSenha}
                  onChange={(e) => {
                    setNovaSenha(e.target.value);
                  }}
                />
                <Botao type="submit" variante="acao" disabled={enviando}>
                  Confirmar
                </Botao>
              </form>
            )}
            {erro !== null && (
              <MensagemErro
                erro={erro}
                texto={proprio ? "Você não pode desativar o próprio usuário." : null}
              />
            )}
            {aviso && (
              <p role="status" className="font-semibold text-verde">
                {aviso}
              </p>
            )}
          </td>
        </tr>
      )}
    </>
  );
}

function FormNovoUsuario({ aoCriar }: { aoCriar: () => void }) {
  const vazio = { nome: "", login: "", perfil: "", senha: "" };
  const [dados, setDados] = useState(vazio);
  const [perfis, setPerfis] = useState<ListaPerfis | null>(null);
  const [erroPerfis, setErroPerfis] = useState<unknown>(null);
  const [tentativa, setTentativa] = useState(0);
  const [erro, setErro] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let ativo = true;
    listarPerfis().then(
      (p) => {
        if (ativo) setPerfis(p);
      },
      (e: unknown) => {
        if (ativo) setErroPerfis(e);
      },
    );
    return () => {
      ativo = false;
    };
  }, [tentativa]);

  if (erroPerfis !== null) {
    return (
      <MensagemErro
        erro={erroPerfis}
        aoTentarNovamente={() => {
          setErroPerfis(null);
          setTentativa((t) => t + 1);
        }}
      />
    );
  }
  if (!perfis) return null;

  const erroCampo = (campo: keyof typeof vazio) => {
    const codigos = codigosCampo(erro, campo);
    if (codigos.length === 0) return undefined;
    if (campo === "login" && erro instanceof ErroRequisicao && erro.status === 409) {
      return "Já existe um usuário com esse login.";
    }
    return "Confira este campo.";
  };
  const mudar = (campo: keyof typeof vazio) => (valor: string) => {
    setDados({ ...dados, [campo]: valor });
  };
  const enviar = (evento: SyntheticEvent) => {
    evento.preventDefault();
    setEnviando(true);
    setErro(null);
    usuarios.criar(dados).then(
      () => {
        setEnviando(false);
        setDados(vazio);
        aoCriar();
      },
      (e: unknown) => {
        setEnviando(false);
        setErro(e);
      },
    );
  };
  const erroPerfil = erroCampo("perfil");
  const temErroDeCampo = (["nome", "login", "perfil", "senha"] as const).some((c) => erroCampo(c));

  return (
    <section className="max-w-xl border-t border-fio pt-6">
      <h2 className="mb-4 text-xl font-bold">Novo usuário</h2>
      <form onSubmit={enviar} className="grid gap-4 sm:grid-cols-2">
        <Campo
          rotulo="Nome"
          required
          value={dados.nome}
          erro={erroCampo("nome")}
          onChange={(e) => {
            mudar("nome")(e.target.value);
          }}
        />
        <Campo
          rotulo="Login"
          required
          autoComplete="off"
          value={dados.login}
          erro={erroCampo("login")}
          onChange={(e) => {
            mudar("login")(e.target.value);
          }}
        />
        <div className="flex flex-col gap-1">
          <label htmlFor="novo-usuario-perfil" className="text-sm font-semibold">
            Perfil
          </label>
          <select
            id="novo-usuario-perfil"
            required
            value={dados.perfil}
            aria-invalid={erroPerfil ? true : undefined}
            className={CLASSE_ENTRADA}
            onChange={(e) => {
              mudar("perfil")(e.target.value);
            }}
          >
            <option value="">Escolha</option>
            {perfis.itens.map((p) => (
              <option key={p.codigo} value={p.codigo}>
                {nomePerfil(p.codigo)}
              </option>
            ))}
          </select>
          {erroPerfil && <p className="text-sm font-semibold text-vermelho">{erroPerfil}</p>}
        </div>
        <Campo
          rotulo="Senha"
          type="password"
          autoComplete="new-password"
          required
          value={dados.senha}
          erro={erroCampo("senha")}
          onChange={(e) => {
            mudar("senha")(e.target.value);
          }}
        />
        {erro !== null && !temErroDeCampo && (
          <div className="sm:col-span-2">
            <MensagemErro erro={erro} />
          </div>
        )}
        <Botao type="submit" variante="acao" disabled={enviando} className="justify-self-start">
          Criar usuário
        </Botao>
      </form>
    </section>
  );
}
