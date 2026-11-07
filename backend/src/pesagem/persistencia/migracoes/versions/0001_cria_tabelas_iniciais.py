"""Cria as tabelas iniciais (spec 014 §5).

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Situações que reservam a balança (spec 006 §6.3; spec 014 §6).
_RESERVAM_BALANCA = """
'AUTORIZADA', 'ENTRADA_LIBERADA', 'FECHANDO_ENTRADA', 'POSICIONADA_INICIAL',
'PESO_INICIAL_OK', 'SAIDA_INICIAL_LIBERADA', 'FECHANDO_SAIDA_INICIAL',
'RETORNO_AUTORIZADO', 'RETORNO_LIBERADO', 'FECHANDO_ENTRADA_RETORNO',
'POSICIONADA_FINAL', 'PESO_FINAL_OK', 'SAIDA_LIBERADA', 'FECHANDO_SAIDA'
"""
_NAO_TERMINAIS = f"""
'AGUARDANDO_BALANCA_INICIAL', 'EM_CARGA_DESCARGA', 'AGUARDANDO_BALANCA_FINAL',
{_RESERVAM_BALANCA}
"""
_SITUACOES = f"{_NAO_TERMINAIS}, 'AGUARDANDO_INTERVENCAO', 'FINALIZADA', 'CANCELADA'"

# ADR-0004 §4.3.
_PERMISSOES = {
    "ADMINISTRADOR": [
        "CONSULTAR_OPERACAO",
        "CONSULTAR_IMAGENS_DECISAO",
        "CONSULTAR_IMAGENS_TEMPO_REAL",
        "EXCLUIR_IMAGENS_DECISAO",
        "TENTAR_NOVAMENTE",
        "LIBERAR_CAMINHAO_CANCELADO",
        "INTERVIR_OPERACAO",
        "CRIAR_AGENDAMENTO",
        "CONSULTAR_AGENDAMENTOS",
        "GERENCIAR_AGENDAMENTOS",
        "CONSULTAR_CADASTROS",
        "GERENCIAR_CADASTROS",
        "GERENCIAR_USUARIOS",
    ],
    "OPERADOR": [
        "CONSULTAR_OPERACAO",
        "CONSULTAR_IMAGENS_DECISAO",
        "CONSULTAR_IMAGENS_TEMPO_REAL",
        "TENTAR_NOVAMENTE",
        "LIBERAR_CAMINHAO_CANCELADO",
        "CRIAR_AGENDAMENTO",
        "CONSULTAR_AGENDAMENTOS",
        "CONSULTAR_CADASTROS",
    ],
    "AUDITOR": [
        "CONSULTAR_OPERACAO",
        "CONSULTAR_IMAGENS_DECISAO",
        "CONSULTAR_AGENDAMENTOS",
    ],
}

_TABELAS = """
CREATE TABLE perfil (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  codigo VARCHAR(30) NOT NULL,
  CONSTRAINT pk_perfil PRIMARY KEY (id),
  CONSTRAINT ux_perfil_codigo UNIQUE (codigo)
);

CREATE TABLE perfil_permissao (
  perfil_id INTEGER NOT NULL,
  permissao VARCHAR(50) NOT NULL,
  CONSTRAINT pk_perfil_permissao PRIMARY KEY (perfil_id, permissao),
  CONSTRAINT fk_perfil_permissao_perfil_id FOREIGN KEY (perfil_id) REFERENCES perfil(id)
);

CREATE TABLE usuario (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  nome VARCHAR(100) NOT NULL,
  login VARCHAR(50) NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  perfil_id INTEGER NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  criado_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT pk_usuario PRIMARY KEY (id),
  CONSTRAINT fk_usuario_perfil_id FOREIGN KEY (perfil_id) REFERENCES perfil(id)
);
CREATE UNIQUE INDEX ux_usuario_login ON usuario (lower(login));

CREATE TABLE sessao (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  usuario_id INTEGER NOT NULL,
  hash_identificador CHAR(64) NOT NULL,
  criada_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  ultimo_uso_em TIMESTAMPTZ NOT NULL,
  encerrada_em TIMESTAMPTZ,
  CONSTRAINT pk_sessao PRIMARY KEY (id),
  CONSTRAINT ux_sessao_hash_identificador UNIQUE (hash_identificador),
  CONSTRAINT fk_sessao_usuario_id FOREIGN KEY (usuario_id) REFERENCES usuario(id)
);
CREATE INDEX ix_sessao_usuario_id ON sessao (usuario_id);

CREATE TABLE tentativa_acesso (
  tipo VARCHAR(30) NOT NULL,
  chave CHAR(64) NOT NULL,
  falhas_seguidas INTEGER NOT NULL,
  bloqueado_ate TIMESTAMPTZ,
  CONSTRAINT pk_tentativa_acesso PRIMARY KEY (tipo, chave),
  CONSTRAINT ck_tentativa_acesso_tipo CHECK (tipo IN ('LOGIN', 'AUTOATENDIMENTO')),
  CONSTRAINT ck_tentativa_acesso_falhas CHECK (falhas_seguidas >= 0)
);

CREATE TABLE transportadora (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  razao_social VARCHAR(100) NOT NULL,
  nome_fantasia VARCHAR(100),
  cnpj VARCHAR(14) NOT NULL,
  telefone VARCHAR(15),
  email VARCHAR(100),
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_transportadora PRIMARY KEY (id),
  CONSTRAINT ux_transportadora_cnpj UNIQUE (cnpj)
);

CREATE TABLE motorista (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  transportadora_id INTEGER,
  nome VARCHAR(100) NOT NULL,
  cpf VARCHAR(11) NOT NULL,
  cnh_numero VARCHAR(20),
  cnh_categoria VARCHAR(2),
  data_validade_cnh DATE,
  telefone VARCHAR(15),
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_motorista PRIMARY KEY (id),
  CONSTRAINT ux_motorista_cpf UNIQUE (cpf),
  CONSTRAINT fk_motorista_transportadora_id FOREIGN KEY (transportadora_id) REFERENCES transportadora(id)
);

CREATE TABLE tipo_veiculo (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(100) NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_tipo_veiculo PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ux_tipo_veiculo_descricao ON tipo_veiculo (lower(descricao));

CREATE TABLE veiculo (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  placa VARCHAR(7) NOT NULL,
  chave_comparacao VARCHAR(7) NOT NULL,
  tipo_veiculo_id INTEGER NOT NULL,
  transportadora_id INTEGER,
  motorista_padrao_id INTEGER,
  marca VARCHAR(30),
  modelo VARCHAR(30),
  eixos SMALLINT,
  tara_kg NUMERIC(12,3),
  capacidade_kg NUMERIC(12,3),
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_veiculo PRIMARY KEY (id),
  CONSTRAINT ux_veiculo_chave_comparacao UNIQUE (chave_comparacao),
  CONSTRAINT fk_veiculo_tipo_veiculo_id FOREIGN KEY (tipo_veiculo_id) REFERENCES tipo_veiculo(id),
  CONSTRAINT fk_veiculo_transportadora_id FOREIGN KEY (transportadora_id) REFERENCES transportadora(id),
  CONSTRAINT fk_veiculo_motorista_padrao_id FOREIGN KEY (motorista_padrao_id) REFERENCES motorista(id),
  CONSTRAINT ck_veiculo_eixos CHECK (eixos IS NULL OR eixos > 0),
  CONSTRAINT ck_veiculo_tara CHECK (tara_kg IS NULL OR tara_kg >= 0),
  CONSTRAINT ck_veiculo_capacidade CHECK (capacidade_kg IS NULL OR capacidade_kg > 0)
);

CREATE TABLE produto (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  codigo VARCHAR(30) NOT NULL,
  descricao VARCHAR(100) NOT NULL,
  unidade VARCHAR(5) DEFAULT 'KG' NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_produto PRIMARY KEY (id),
  CONSTRAINT ux_produto_codigo UNIQUE (codigo)
);

CREATE TABLE balanca (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(50) NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_balanca PRIMARY KEY (id),
  CONSTRAINT ux_balanca_descricao UNIQUE (descricao)
);

CREATE TABLE cancela (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(100) NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_cancela PRIMARY KEY (id),
  CONSTRAINT ux_cancela_descricao UNIQUE (descricao)
);

CREATE TABLE ponto_controle (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  nome VARCHAR(50) NOT NULL,
  balanca_id INTEGER NOT NULL,
  cancela_entrada_id INTEGER NOT NULL,
  cancela_saida_id INTEGER NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_ponto_controle PRIMARY KEY (id),
  CONSTRAINT ux_ponto_controle_nome UNIQUE (nome),
  CONSTRAINT ux_ponto_controle_balanca_id UNIQUE (balanca_id),
  CONSTRAINT fk_ponto_controle_balanca_id FOREIGN KEY (balanca_id) REFERENCES balanca(id),
  CONSTRAINT fk_ponto_controle_cancela_entrada_id FOREIGN KEY (cancela_entrada_id) REFERENCES cancela(id),
  CONSTRAINT fk_ponto_controle_cancela_saida_id FOREIGN KEY (cancela_saida_id) REFERENCES cancela(id)
);

CREATE TABLE camera (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(100) NOT NULL,
  ponto_controle_id INTEGER NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_camera PRIMARY KEY (id),
  CONSTRAINT ux_camera_descricao UNIQUE (descricao),
  CONSTRAINT fk_camera_ponto_controle_id FOREIGN KEY (ponto_controle_id) REFERENCES ponto_controle(id)
);

CREATE TABLE faixa_horario (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  hora_inicio TIME NOT NULL,
  hora_fim TIME NOT NULL,
  capacidade INTEGER NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_faixa_horario PRIMARY KEY (id),
  CONSTRAINT ck_faixa_horario_horas CHECK (hora_fim > hora_inicio),
  CONSTRAINT ck_faixa_horario_capacidade CHECK (capacidade > 0),
  -- Data fixa só para formar o intervalo; [início, fim) aceita faixas vizinhas.
  CONSTRAINT ex_faixa_horario_sobreposta EXCLUDE USING gist (
    tsrange(DATE '2000-01-01' + hora_inicio, DATE '2000-01-01' + hora_fim) WITH &&
  ) WHERE (ativo)
);

CREATE TABLE agendamento (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  veiculo_id INTEGER NOT NULL,
  motorista_id INTEGER NOT NULL,
  transportadora_id INTEGER,
  produto_id INTEGER NOT NULL,
  tipo_operacao VARCHAR(30) NOT NULL,
  data_prevista DATE NOT NULL,
  faixa_horario_id INTEGER NOT NULL,
  codigo_nota VARCHAR(100),
  observacao VARCHAR(200),
  status VARCHAR(30) NOT NULL DEFAULT 'AGENDADO',
  origem VARCHAR(30) NOT NULL,
  criado_por INTEGER,
  criado_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  cancelado_por INTEGER,
  cancelado_em TIMESTAMPTZ,
  motivo_cancelamento VARCHAR(200),
  CONSTRAINT pk_agendamento PRIMARY KEY (id),
  CONSTRAINT fk_agendamento_veiculo_id FOREIGN KEY (veiculo_id) REFERENCES veiculo(id),
  CONSTRAINT fk_agendamento_motorista_id FOREIGN KEY (motorista_id) REFERENCES motorista(id),
  CONSTRAINT fk_agendamento_transportadora_id FOREIGN KEY (transportadora_id) REFERENCES transportadora(id),
  CONSTRAINT fk_agendamento_produto_id FOREIGN KEY (produto_id) REFERENCES produto(id),
  CONSTRAINT fk_agendamento_faixa_horario_id FOREIGN KEY (faixa_horario_id) REFERENCES faixa_horario(id),
  CONSTRAINT fk_agendamento_criado_por FOREIGN KEY (criado_por) REFERENCES usuario(id),
  CONSTRAINT fk_agendamento_cancelado_por FOREIGN KEY (cancelado_por) REFERENCES usuario(id),
  CONSTRAINT ck_agendamento_tipo_operacao CHECK (tipo_operacao IN ('CARGA', 'DESCARGA')),
  CONSTRAINT ck_agendamento_status CHECK (status IN ('AGENDADO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO', 'EXPIRADO')),
  CONSTRAINT ck_agendamento_origem CHECK (origem IN ('USUARIO', 'AUTOATENDIMENTO')),
  CONSTRAINT ck_agendamento_criado_por CHECK ((origem = 'USUARIO') = (criado_por IS NOT NULL)),
  CONSTRAINT ck_agendamento_codigo_nota CHECK (codigo_nota IS NULL OR tipo_operacao = 'DESCARGA'),
  CONSTRAINT ck_agendamento_cancelamento CHECK (
    (status = 'CANCELADO') = (cancelado_por IS NOT NULL)
    AND (status = 'CANCELADO') = (cancelado_em IS NOT NULL)
    AND (status = 'CANCELADO') = (motivo_cancelamento IS NOT NULL))
);
CREATE UNIQUE INDEX ux_agendamento_veiculo_aberto ON agendamento (veiculo_id)
  WHERE status IN ('AGENDADO', 'EM_ANDAMENTO');
CREATE INDEX ix_agendamento_faixa_horario_id_data_prevista ON agendamento (faixa_horario_id, data_prevista);

CREATE TABLE pesagem (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  agendamento_id INTEGER NOT NULL,
  ponto_controle_id INTEGER NOT NULL,
  veiculo_id INTEGER NOT NULL,
  motorista_id INTEGER NOT NULL,
  placa VARCHAR(7) NOT NULL,
  chave_comparacao VARCHAR(7) NOT NULL,
  tipo_operacao VARCHAR(30) NOT NULL,
  situacao VARCHAR(30) NOT NULL,
  situacao_anterior VARCHAR(30),
  motivo_intervencao VARCHAR(30),
  versao INTEGER NOT NULL,
  peso_inicial_kg NUMERIC(12,3),
  peso_inicial_em TIMESTAMPTZ,
  peso_final_kg NUMERIC(12,3),
  peso_final_em TIMESTAMPTZ,
  peso_liquido_kg NUMERIC(12,3),
  classificacao VARCHAR(30),
  liberacao_manual BOOLEAN DEFAULT FALSE NOT NULL,
  -- Ordem da fila e tempos-limite depois de um reinício (spec 015).
  situacao_desde TIMESTAMPTZ NOT NULL,
  -- Caminhão de operação cancelada ainda na balança (spec 006 §6.4).
  aguarda_liberacao_balanca BOOLEAN DEFAULT FALSE NOT NULL,
  criado_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT pk_pesagem PRIMARY KEY (id),
  CONSTRAINT fk_pesagem_agendamento_id FOREIGN KEY (agendamento_id) REFERENCES agendamento(id),
  CONSTRAINT fk_pesagem_ponto_controle_id FOREIGN KEY (ponto_controle_id) REFERENCES ponto_controle(id),
  CONSTRAINT fk_pesagem_veiculo_id FOREIGN KEY (veiculo_id) REFERENCES veiculo(id),
  CONSTRAINT fk_pesagem_motorista_id FOREIGN KEY (motorista_id) REFERENCES motorista(id),
  CONSTRAINT ck_pesagem_tipo_operacao CHECK (tipo_operacao IN ('CARGA', 'DESCARGA')),
  CONSTRAINT ck_pesagem_situacao CHECK (situacao IN (__SITUACOES__)),
  CONSTRAINT ck_pesagem_situacao_anterior CHECK (situacao_anterior IN (__NAO_TERMINAIS__)),
  CONSTRAINT ck_pesagem_motivo_intervencao CHECK (motivo_intervencao IN (
    'CANCELA_FALHA', 'CANCELA_SEM_CONFIRMACAO', 'POSICAO_PERDIDA', 'TEMPO_ESGOTADO',
    'LIQUIDO_NEGATIVO', 'REINICIO_INCONCLUSIVO')),
  CONSTRAINT ck_pesagem_intervencao CHECK (
    (situacao = 'AGUARDANDO_INTERVENCAO') = (situacao_anterior IS NOT NULL)
    AND (situacao = 'AGUARDANDO_INTERVENCAO') = (motivo_intervencao IS NOT NULL)),
  CONSTRAINT ck_pesagem_versao CHECK (versao >= 1),
  CONSTRAINT ck_pesagem_pesos CHECK (COALESCE(peso_inicial_kg, 0) >= 0 AND COALESCE(peso_final_kg, 0) >= 0),
  CONSTRAINT ck_pesagem_peso_inicial CHECK ((peso_inicial_kg IS NULL) = (peso_inicial_em IS NULL)),
  CONSTRAINT ck_pesagem_peso_final CHECK ((peso_final_kg IS NULL) = (peso_final_em IS NULL)),
  -- RN-006: o domínio calcula; o banco confere.
  CONSTRAINT ck_pesagem_peso_liquido CHECK (peso_liquido_kg IS NULL OR peso_liquido_kg =
    CASE WHEN tipo_operacao = 'DESCARGA' THEN peso_inicial_kg - peso_final_kg
         ELSE peso_final_kg - peso_inicial_kg END),
  CONSTRAINT ck_pesagem_classificacao CHECK (
    (classificacao IS NULL) = (peso_liquido_kg IS NULL)
    AND classificacao IN ('COM_MOVIMENTACAO', 'SEM_MOVIMENTACAO', 'NEGATIVO_FORA_TOLERANCIA')),
  CONSTRAINT ck_pesagem_final CHECK (situacao <> 'FINALIZADA' OR peso_liquido_kg IS NOT NULL),
  CONSTRAINT ck_pesagem_aguarda_liberacao CHECK (NOT aguarda_liberacao_balanca OR situacao = 'CANCELADA')
);
CREATE UNIQUE INDEX ux_pesagem_agendamento_id ON pesagem (agendamento_id)
  WHERE situacao <> 'CANCELADA';
CREATE UNIQUE INDEX ux_pesagem_veiculo_aberta ON pesagem (veiculo_id)
  WHERE situacao NOT IN ('FINALIZADA', 'CANCELADA');
CREATE UNIQUE INDEX ux_pesagem_balanca_reservada ON pesagem (ponto_controle_id)
  WHERE situacao IN (__RESERVAM__)
     OR (situacao = 'AGUARDANDO_INTERVENCAO' AND situacao_anterior IN (__RESERVAM__));
CREATE INDEX ix_pesagem_criado_em ON pesagem (criado_em, id);
CREATE INDEX ix_pesagem_agendamento_id ON pesagem (agendamento_id);
CREATE INDEX ix_pesagem_chave_comparacao ON pesagem (chave_comparacao);

-- RN-022: só as imagens das decisões; a exclusão apaga os bytes e registra quem e por quê.
CREATE TABLE imagem_decisao (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  conteudo BYTEA,
  origem VARCHAR(100) NOT NULL,
  capturada_em TIMESTAMPTZ NOT NULL,
  roi_x INTEGER,
  roi_y INTEGER,
  roi_largura INTEGER,
  roi_altura INTEGER,
  excluida_por INTEGER,
  excluida_em TIMESTAMPTZ,
  motivo_exclusao VARCHAR(500),
  CONSTRAINT pk_imagem_decisao PRIMARY KEY (id),
  CONSTRAINT fk_imagem_decisao_excluida_por FOREIGN KEY (excluida_por) REFERENCES usuario(id),
  CONSTRAINT ck_imagem_decisao_roi CHECK (num_nulls(roi_x, roi_y, roi_largura, roi_altura) IN (0, 4)),
  CONSTRAINT ck_imagem_decisao_exclusao CHECK (
    (conteudo IS NULL) = (excluida_por IS NOT NULL)
    AND (conteudo IS NULL) = (excluida_em IS NOT NULL)
    AND (conteudo IS NULL) = (motivo_exclusao IS NOT NULL))
);

CREATE TABLE leitura_placa (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  pesagem_id INTEGER,
  agendamento_id INTEGER,
  imagem_id INTEGER,
  origem VARCHAR(100) NOT NULL,
  capturada_em TIMESTAMPTZ NOT NULL,
  decidida_em TIMESTAMPTZ NOT NULL,
  decisao VARCHAR(30) NOT NULL,
  motivo VARCHAR(40),
  placa_lida VARCHAR(20),
  placa_normalizada VARCHAR(7),
  formato VARCHAR(10),
  correcoes JSONB,
  confianca NUMERIC(4,3),
  leituras JSONB NOT NULL,
  CONSTRAINT pk_leitura_placa PRIMARY KEY (id),
  CONSTRAINT fk_leitura_placa_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT fk_leitura_placa_agendamento_id FOREIGN KEY (agendamento_id) REFERENCES agendamento(id),
  CONSTRAINT fk_leitura_placa_imagem_id FOREIGN KEY (imagem_id) REFERENCES imagem_decisao(id),
  CONSTRAINT ck_leitura_placa_decisao CHECK (decisao IN ('AUTORIZADA', 'RETORNO_ACEITO', 'NAO_AUTORIZADA')),
  -- Spec 009 §5.3.
  CONSTRAINT ck_leitura_placa_motivo CHECK ((decisao = 'NAO_AUTORIZADA') = (motivo IS NOT NULL)
    AND motivo IN ('FALHA_IMAGEM', 'FALHA_LEITOR', 'SEM_CANDIDATO', 'PLACA_INVALIDA',
      'AMBIGUA', 'CONFIANCA_BAIXA', 'VEICULO_NAO_CADASTRADO', 'VEICULO_INATIVO',
      'OPERACAO_JA_ABERTA', 'SEM_AGENDAMENTO', 'AGENDAMENTO_AMBIGUO', 'MOTORISTA_INATIVO',
      'ANTES_DA_FAIXA')),
  CONSTRAINT ck_leitura_placa_formato CHECK (formato IN ('ANTIGO', 'MERCOSUL')),
  CONSTRAINT ck_leitura_placa_confianca CHECK (confianca BETWEEN 0 AND 1)
);
CREATE INDEX ix_leitura_placa_decidida_em ON leitura_placa (decidida_em, id);
CREATE INDEX ix_leitura_placa_pesagem_id ON leitura_placa (pesagem_id);

-- Caminhão de operação cancelada na balança (spec 006 §6.4, spec 009 §5.6): uma por pesagem.
CREATE TABLE liberacao_caminhao (
  pesagem_id INTEGER NOT NULL,
  etapa VARCHAR(30) NOT NULL,
  motivo_falha VARCHAR(30),
  pedido_por INTEGER,
  motivo VARCHAR(200),
  pedida_em TIMESTAMPTZ,
  atualizada_em TIMESTAMPTZ NOT NULL,
  CONSTRAINT pk_liberacao_caminhao PRIMARY KEY (pesagem_id),
  CONSTRAINT fk_liberacao_caminhao_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT fk_liberacao_caminhao_pedido_por FOREIGN KEY (pedido_por) REFERENCES usuario(id),
  CONSTRAINT ck_liberacao_caminhao_etapa CHECK (etapa IN ('PENDENTE', 'ABRINDO_SAIDA',
    'AGUARDANDO_BALANCA_VAZIA', 'FECHANDO_SAIDA', 'CONCLUIDA', 'FALHOU')),
  CONSTRAINT ck_liberacao_caminhao_falha CHECK ((etapa = 'FALHOU') = (motivo_falha IS NOT NULL)
    AND motivo_falha IN ('CANCELA_FALHA', 'CANCELA_SEM_CONFIRMACAO', 'TEMPO_ESGOTADO')),
  CONSTRAINT ck_liberacao_caminhao_pedido CHECK (
    (etapa = 'PENDENTE') = (pedido_por IS NULL)
    AND (pedido_por IS NULL) = (motivo IS NULL)
    AND (pedido_por IS NULL) = (pedida_em IS NULL))
);

CREATE TABLE evento_operacao (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  pesagem_id INTEGER NOT NULL,
  tipo_registro VARCHAR(30) NOT NULL,
  evento VARCHAR(40) NOT NULL,
  situacao_origem VARCHAR(30),
  situacao_destino VARCHAR(30),
  motivo_rejeicao VARCHAR(40),
  motivo_intervencao VARCHAR(30),
  motivo_dispositivo VARCHAR(40),
  peso_kg NUMERIC(12,3),
  peso_liquido_kg NUMERIC(12,3),
  classificacao VARCHAR(30),
  cancela VARCHAR(10),
  comando VARCHAR(10),
  resultado VARCHAR(30),
  tentativas SMALLINT,
  leitura_placa_id INTEGER,
  imagem_id INTEGER,
  responsavel_id INTEGER,
  motivo VARCHAR(200),
  ocorrido_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT pk_evento_operacao PRIMARY KEY (id),
  CONSTRAINT fk_evento_operacao_leitura_placa_id FOREIGN KEY (leitura_placa_id) REFERENCES leitura_placa(id),
  CONSTRAINT fk_evento_operacao_imagem_id FOREIGN KEY (imagem_id) REFERENCES imagem_decisao(id),
  CONSTRAINT fk_evento_operacao_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT fk_evento_operacao_responsavel_id FOREIGN KEY (responsavel_id) REFERENCES usuario(id),
  CONSTRAINT ck_evento_operacao_tipo_registro CHECK (tipo_registro IN (
    'TRANSICAO', 'TRANSICAO_REJEITADA', 'EVENTO_REGISTRADO', 'COMANDO_CANCELA')),
  CONSTRAINT ck_evento_operacao_origem CHECK (situacao_origem IS NOT NULL OR evento = 'CRIACAO'),
  CONSTRAINT ck_evento_operacao_destino CHECK ((tipo_registro = 'TRANSICAO') = (situacao_destino IS NOT NULL)),
  CONSTRAINT ck_evento_operacao_rejeicao CHECK ((tipo_registro = 'TRANSICAO_REJEITADA') = (motivo_rejeicao IS NOT NULL)),
  CONSTRAINT ck_evento_operacao_cancela CHECK ((tipo_registro = 'COMANDO_CANCELA') = (
    cancela IS NOT NULL AND comando IS NOT NULL AND resultado IS NOT NULL AND tentativas IS NOT NULL)),
  CONSTRAINT ck_evento_operacao_cancela_valores CHECK (cancela IN ('ENTRADA', 'SAIDA')
    AND comando IN ('ABRIR', 'FECHAR') AND resultado IN ('CONFIRMADO', 'FALHA', 'SEM_CONFIRMACAO')
    AND tentativas >= 1),
  CONSTRAINT ck_evento_operacao_responsavel CHECK ((responsavel_id IS NULL) = (motivo IS NULL))
);
CREATE INDEX ix_evento_operacao_pesagem_id ON evento_operacao (pesagem_id, ocorrido_em, id);

CREATE TABLE registro_auditoria (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  tipo VARCHAR(30) NOT NULL,
  responsavel_id INTEGER,
  usuario_afetado_id INTEGER,
  agendamento_id INTEGER,
  endereco_origem VARCHAR(45),
  ocorrido_em TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT pk_registro_auditoria PRIMARY KEY (id),
  CONSTRAINT fk_registro_auditoria_responsavel_id FOREIGN KEY (responsavel_id) REFERENCES usuario(id),
  CONSTRAINT fk_registro_auditoria_usuario_afetado_id FOREIGN KEY (usuario_afetado_id) REFERENCES usuario(id),
  CONSTRAINT fk_registro_auditoria_agendamento_id FOREIGN KEY (agendamento_id) REFERENCES agendamento(id),
  CONSTRAINT ck_registro_auditoria_tipo CHECK (tipo IN (
    'LOGIN_ACEITO', 'LOGIN_RECUSADO', 'LOGIN_BLOQUEADO', 'LOGOUT', 'USUARIO_CRIADO',
    'USUARIO_DESATIVADO', 'USUARIO_REATIVADO', 'SENHA_REDEFINIDA',
    'AGENDAMENTO_EDITADO', 'AGENDAMENTO_CANCELADO', 'AUTOATENDIMENTO_RECUSADO'))
);
CREATE INDEX ix_registro_auditoria_ocorrido_em ON registro_auditoria (ocorrido_em);
"""

_ORDEM_REMOCAO = (
    "registro_auditoria, evento_operacao, liberacao_caminhao, leitura_placa, imagem_decisao, pesagem, agendamento, "
    "faixa_horario, camera, ponto_controle, cancela, balanca, produto, veiculo, "
    "tipo_veiculo, motorista, transportadora, tentativa_acesso, sessao, usuario, "
    "perfil_permissao, perfil"
)


def upgrade() -> None:
    op.execute(
        _TABELAS.replace("__SITUACOES__", _SITUACOES)
        .replace("__NAO_TERMINAIS__", _NAO_TERMINAIS)
        .replace("__RESERVAM__", _RESERVAM_BALANCA)
    )
    for codigo, permissoes in _PERMISSOES.items():
        valores = ", ".join(f"('{p}')" for p in permissoes)
        op.execute(
            f"WITH p AS (INSERT INTO perfil (codigo) VALUES ('{codigo}') RETURNING id) "
            f"INSERT INTO perfil_permissao (perfil_id, permissao) "
            f"SELECT p.id, v.permissao FROM p, (VALUES {valores}) AS v (permissao)"
        )


def downgrade() -> None:
    op.execute(f"DROP TABLE {_ORDEM_REMOCAO}")
