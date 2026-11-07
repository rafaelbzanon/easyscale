"""Conexão e transação (ADR-0006; spec 014 §7.4 e §9).

Síncrono: quem está num laço assíncrono chama com `asyncio.to_thread`.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import URL, Connection, create_engine
from sqlalchemy import (
    Engine as Engine,  # reexportado: só a persistência importa sqlalchemy
)
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError

from pesagem.config import ConfiguracaoBanco
from pesagem.persistencia.erros import (
    ErroBalancaOcupada,
    ErroBancoIndisponivel,
    ErroDuplicidade,
    ErroFaixaSobreposta,
    ErroOperacaoAberta,
    ErroPersistencia,
    ErroVeiculoJaAgendado,
)
from pesagem.persistencia.repositorios.acesso import RepositorioAcesso
from pesagem.persistencia.repositorios.agendamento import RepositorioAgendamento
from pesagem.persistencia.repositorios.cadastro import RepositorioCadastro
from pesagem.persistencia.repositorios.faixa_horario import RepositorioFaixaHorario
from pesagem.persistencia.repositorios.imagem import RepositorioImagem
from pesagem.persistencia.repositorios.leitura_placa import RepositorioLeituraPlaca
from pesagem.persistencia.repositorios.pesagem import RepositorioPesagem
from pesagem.persistencia.repositorios.ponto_controle import RepositorioPontoControle
from pesagem.persistencia.repositorios.usuario import RepositorioUsuario
from pesagem.persistencia.repositorios.veiculo import RepositorioVeiculo

# Restrição -> erro próprio (spec 014 §6). Os nomes vêm da migração 0001.
_ERROS_POR_RESTRICAO: dict[str, type[ErroPersistencia]] = {
    "ux_pesagem_balanca_reservada": ErroBalancaOcupada,
    "ux_pesagem_veiculo_aberta": ErroOperacaoAberta,
    "ux_pesagem_agendamento_id": ErroOperacaoAberta,
    "ux_agendamento_veiculo_aberto": ErroVeiculoJaAgendado,
    "ex_faixa_horario_sobreposta": ErroFaixaSobreposta,
}


def criar_engine(configuracao: ConfiguracaoBanco) -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=configuracao.usuario,
        password=configuracao.senha,
        host=configuracao.host,
        port=configuracao.porta,
        database=configuracao.nome,
    )
    return create_engine(url, pool_pre_ping=True)


class Transacao:
    """Repositórios ligados a uma mesma transação: tudo sai junto ou nada sai."""

    def __init__(self, conexao: Connection) -> None:
        self.conexao = conexao
        self.pesagens = RepositorioPesagem(conexao)
        self.agendamentos = RepositorioAgendamento(conexao)
        self.veiculos = RepositorioVeiculo(conexao)
        self.leituras_placa = RepositorioLeituraPlaca(conexao)
        self.imagens = RepositorioImagem(conexao)
        self.pontos_controle = RepositorioPontoControle(conexao)
        self.usuarios = RepositorioUsuario(conexao)
        self.acesso = RepositorioAcesso(conexao)
        self.cadastros = RepositorioCadastro(conexao)
        self.faixas = RepositorioFaixaHorario(conexao)


@contextmanager
def transacao(engine: Engine) -> Iterator[Transacao]:
    """Confirma ao sair sem erro; desfaz tudo se houver exceção (CA-014).

    As violações de restrição viram os erros da spec 014 §6 ao sair do bloco.
    """
    try:
        with engine.begin() as conexao:
            yield Transacao(conexao)
    except IntegrityError as erro:
        raise _traduzir(erro) from None
    # Sem detalhe do driver para fora: só o tipo do erro (RNF-013).
    except OperationalError as erro:
        raise ErroBancoIndisponivel(type(erro.orig).__name__) from None
    except DBAPIError as erro:
        raise ErroPersistencia(type(erro.orig).__name__) from None


def _traduzir(erro: IntegrityError) -> ErroPersistencia:
    restricao = getattr(getattr(erro.orig, "diag", None), "constraint_name", None)
    if restricao in _ERROS_POR_RESTRICAO:
        return _ERROS_POR_RESTRICAO[restricao](restricao)
    if restricao and restricao.startswith("ux_"):
        return ErroDuplicidade(restricao)
    return ErroPersistencia(restricao or "restricao_desconhecida")
