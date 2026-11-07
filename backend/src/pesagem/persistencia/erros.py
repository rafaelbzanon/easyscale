"""Erros da persistência (spec 014 §6 e §9; `CONVENCOES.md` §4.5).

A exceção do driver nunca sai de `persistencia/`.
"""


class ErroPersistencia(Exception):
    """Base. Também cobre violação de restrição não prevista."""


class ErroBancoIndisponivel(ErroPersistencia):
    pass


class ErroNaoEncontrado(ErroPersistencia):
    pass


class ErroConflitoVersao(ErroPersistencia):
    """Outra gravação mudou a operação antes: releia e reavalie (spec 006 §7.3)."""


class ErroBalancaOcupada(ErroPersistencia):
    pass


class ErroOperacaoAberta(ErroPersistencia):
    pass


class ErroVeiculoJaAgendado(ErroPersistencia):
    pass


class ErroFaixaSemVaga(ErroPersistencia):
    pass


class ErroFaixaEncerrada(ErroPersistencia):
    pass


class ErroSemFaixaDisponivel(ErroPersistencia):
    pass


class ErroFaixaSobreposta(ErroPersistencia):
    pass


class ErroStatusAgendamento(ErroPersistencia):
    """O agendamento não está `AGENDADO` (spec 008 §6.5 e §6.9)."""


class ErroCodigoNotaNaoPermitido(ErroPersistencia):
    """`codigo_nota` em `CARGA` (spec 008 §6.8)."""


class ErroFaixaComAgendamentos(ErroPersistencia):
    """Mudar o horário de faixa com agendamento ativo (spec 008 §6.7)."""


class ErroLeituraJaUsada(ErroPersistencia):
    """A leitura de placa já gerou uma pesagem (spec 009 §6.5)."""


class ErroLiberacaoIndisponivel(ErroPersistencia):
    """Liberação do caminhão cancelado já em curso ou inexistente (spec 009 §6.6)."""


class ErroDuplicidade(ErroPersistencia):
    def __init__(self, restricao: str) -> None:
        super().__init__(restricao)
        self.restricao = restricao
