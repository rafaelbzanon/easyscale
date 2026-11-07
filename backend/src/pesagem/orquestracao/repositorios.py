"""O que a orquestração usa da persistência (spec 015 §5.4).

`Protocol` com as assinaturas da spec 014, para os testes rodarem com uma
implementação em memória e a real (`pesagem.persistencia`) encaixar sem
adaptação. Chamados sempre em `asyncio.to_thread`.
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date, datetime
from typing import Protocol

from pesagem.dominio.operacao.maquina_estados import (
    EventoOperacao,
    EventoRegistrado,
    Operacao,
    TransicaoRejeitada,
)
from pesagem.persistencia.repositorios.leitura_placa import (
    LeituraPlacaRegistrada,
    NovaLeituraPlaca,
)
from pesagem.persistencia.repositorios.pesagem import (
    LiberacaoCaminhao,
    OperacaoRegistrada,
)
from pesagem.persistencia.repositorios.veiculo import SituacaoVeiculo


class RepositorioPesagens(Protocol):
    def criar_operacao(
        self,
        agendamento_id: int,
        ponto_controle_id: int,
        em: datetime,
        leitura_placa_id: int | None = None,
        liberacao_manual: bool = False,
        responsavel_id: int | None = None,
        motivo: str | None = None,
        *,
        veiculo_id: int,
    ) -> OperacaoRegistrada: ...

    def obter_operacao(self, pesagem_id: int) -> OperacaoRegistrada: ...

    def listar_operacoes_abertas(self) -> list[OperacaoRegistrada]: ...

    def listar_aguardando_liberacao_balanca(self) -> list[OperacaoRegistrada]: ...

    def buscar_liberacao_caminhao(
        self, pesagem_id: int
    ) -> LiberacaoCaminhao | None: ...

    def pedir_liberacao_caminhao(
        self, pesagem_id: int, pedido_por: int, motivo: str, em: datetime
    ) -> None: ...

    def atualizar_liberacao_caminhao(
        self,
        pesagem_id: int,
        etapa: str,
        em: datetime,
        motivo_falha: str | None = None,
    ) -> None: ...

    def gravar_transicao(
        self,
        pesagem_id: int,
        versao_lida: int,
        operacao_nova: Operacao,
        evento: EventoOperacao,
        responsavel_id: int | None,
        hoje: date,
        em: datetime,
        aguarda_liberacao_balanca: bool = False,
        leitura_placa_id: int | None = None,
        imagem_id: int | None = None,
    ) -> None: ...

    def registrar_evento(
        self,
        pesagem_id: int,
        resultado: TransicaoRejeitada | EventoRegistrado,
        responsavel_id: int | None,
        em: datetime,
        motivo_dispositivo: str | None = None,
        leitura_placa_id: int | None = None,
        imagem_id: int | None = None,
    ) -> None: ...

    def registrar_comando_cancela(
        self,
        pesagem_id: int,
        cancela: str,
        comando: str,
        resultado: str,
        tentativas: int,
        em: datetime,
        responsavel_id: int | None = None,
        motivo: str | None = None,
    ) -> None: ...


class RepositorioVeiculos(Protocol):
    def buscar_situacao_por_chave(
        self, chave_comparacao: str
    ) -> SituacaoVeiculo | None: ...

    def buscar_situacao_por_agendamento(
        self, agendamento_id: int
    ) -> SituacaoVeiculo | None: ...


class RepositorioLeiturasPlaca(Protocol):
    def registrar(self, leitura: NovaLeituraPlaca) -> int: ...

    def buscar(self, leitura_placa_id: int) -> LeituraPlacaRegistrada | None: ...


class RepositorioImagens(Protocol):
    def salvar(
        self,
        conteudo: bytes,
        origem: str,
        capturada_em: datetime,
        roi: tuple[int, int, int, int] | None = None,
    ) -> int: ...


class RepositorioPontosControle(Protocol):
    def obter_unico(self) -> int: ...


class Transacao(Protocol):
    # Propriedades, e não atributos: atributo de Protocol é invariante e exigiria
    # o tipo exato, recusando os repositórios da `persistencia`.
    @property
    def pesagens(self) -> RepositorioPesagens: ...

    @property
    def veiculos(self) -> RepositorioVeiculos: ...

    @property
    def leituras_placa(self) -> RepositorioLeiturasPlaca: ...

    @property
    def imagens(self) -> RepositorioImagens: ...

    @property
    def pontos_controle(self) -> RepositorioPontosControle: ...


# Abre uma transação: `functools.partial(pesagem.persistencia.banco.transacao, engine)`.
type Banco = Callable[[], AbstractContextManager[Transacao]]
