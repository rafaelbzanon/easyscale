"""Consulta da autorização (spec 014 §7.3; RN-002, RN-008, RN-014, RN-023)."""

from dataclasses import dataclass
from datetime import date, time

from sqlalchemy import Connection, text


@dataclass(frozen=True)
class OperacaoAbertaDoVeiculo:
    pesagem_id: int
    situacao: str


@dataclass(frozen=True)
class AgendamentoAberto:
    agendamento_id: int
    status: str
    data_prevista: date
    tipo_operacao: str
    faixa_hora_inicio: time
    motorista_ativo: bool


@dataclass(frozen=True)
class SituacaoVeiculo:
    """Retrato para a regra da autorização decidir; o repositório não decide."""

    veiculo_id: int
    ativo: bool
    operacao_aberta: OperacaoAbertaDoVeiculo | None
    agendamentos: tuple[AgendamentoAberto, ...]


class RepositorioVeiculo:
    def __init__(self, conexao: Connection) -> None:
        self._conexao = conexao

    def buscar_situacao_por_chave(
        self, chave_comparacao: str
    ) -> SituacaoVeiculo | None:
        return self._retrato(
            "SELECT id, ativo FROM veiculo WHERE chave_comparacao = :c",
            {"c": chave_comparacao},
        )

    def buscar_situacao_por_agendamento(
        self, agendamento_id: int
    ) -> SituacaoVeiculo | None:
        """Liberação manual de entrada (RN-016): a leitura pode não ter placa."""
        return self._retrato(
            "SELECT v.id, v.ativo FROM veiculo v JOIN agendamento a "
            "ON a.veiculo_id = v.id WHERE a.id = :a",
            {"a": agendamento_id},
        )

    def buscar_ativos_por_placa_e_cpf(
        self, chave_comparacao: str, cpf: str
    ) -> tuple[int, int] | None:
        """(veiculo_id, motorista_id) se os dois existem e estão ativos (RN-021)."""
        linha = self._conexao.execute(
            text(
                "SELECT v.id, m.id FROM veiculo v, motorista m WHERE v.chave_comparacao = :c "
                "AND v.ativo AND m.cpf = :cpf AND m.ativo"
            ),
            {"c": chave_comparacao, "cpf": cpf},
        ).one_or_none()
        return None if linha is None else (int(linha[0]), int(linha[1]))

    def _retrato(
        self, sql: str, parametros: dict[str, object]
    ) -> SituacaoVeiculo | None:
        veiculo = self._conexao.execute(text(sql), parametros).one_or_none()
        if veiculo is None:
            return None
        operacao = self._conexao.execute(
            text(
                "SELECT id, situacao FROM pesagem WHERE veiculo_id = :v "
                "AND situacao NOT IN ('FINALIZADA', 'CANCELADA')"
            ),
            {"v": veiculo.id},
        ).one_or_none()
        agendamentos = self._conexao.execute(
            text(
                "SELECT a.id, a.status, a.data_prevista, a.tipo_operacao, "
                "f.hora_inicio, m.ativo FROM agendamento a "
                "JOIN faixa_horario f ON f.id = a.faixa_horario_id "
                "JOIN motorista m ON m.id = a.motorista_id WHERE a.veiculo_id = :v "
                "AND a.status IN ('AGENDADO', 'EM_ANDAMENTO') ORDER BY a.id"
            ),
            {"v": veiculo.id},
        ).all()
        return SituacaoVeiculo(
            veiculo_id=veiculo.id,
            ativo=veiculo.ativo,
            operacao_aberta=None
            if operacao is None
            else OperacaoAbertaDoVeiculo(operacao.id, operacao.situacao),
            agendamentos=tuple(AgendamentoAberto(*linha) for linha in agendamentos),
        )
