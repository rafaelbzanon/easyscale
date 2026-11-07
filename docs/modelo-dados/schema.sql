-- HISTÓRICO (2026-11-07, spec 014): este arquivo não é mais atualizado.
-- O esquema vigente está nas migrações do Alembic, em
-- backend/src/pesagem/persistencia/migracoes/ (ADR-0006, CONVENCOES.md P-10).
--
-- Modelo de dados do TCC: Automação de Pesagem Rodoviária com LPR
-- Gerado a partir do modelo adaptado do banco legado (banco.grc). PostgreSQL 12+
-- Referência do modelo enquanto não há ferramenta de migração (CONVENCOES.md P-10, D-02).
-- Nomenclatura conforme CONVENCOES.md §1 e §6.

CREATE TABLE usuario (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  nome VARCHAR(100) NOT NULL,
  login VARCHAR(50) NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  perfil VARCHAR(30) NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_usuario PRIMARY KEY (id),
  CONSTRAINT ux_usuario_login UNIQUE (login),
  CONSTRAINT ck_usuario_perfil CHECK (perfil IN ('ADMINISTRADOR', 'OPERADOR'))
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
  rg VARCHAR(20),
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
  CONSTRAINT pk_tipo_veiculo PRIMARY KEY (id),
  CONSTRAINT ux_tipo_veiculo_descricao UNIQUE (descricao)
);

CREATE TABLE veiculo (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  placa VARCHAR(8) NOT NULL,
  tipo_veiculo_id INTEGER NOT NULL,
  transportadora_id INTEGER NOT NULL,
  motorista_padrao_id INTEGER,
  marca VARCHAR(30),
  modelo VARCHAR(30),
  eixos SMALLINT,
  tara_kg NUMERIC(12,3),
  capacidade_kg NUMERIC(12,3),
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_veiculo PRIMARY KEY (id),
  CONSTRAINT ux_veiculo_placa UNIQUE (placa),
  CONSTRAINT fk_veiculo_tipo_veiculo_id FOREIGN KEY (tipo_veiculo_id) REFERENCES tipo_veiculo(id),
  CONSTRAINT fk_veiculo_transportadora_id FOREIGN KEY (transportadora_id) REFERENCES transportadora(id),
  CONSTRAINT fk_veiculo_motorista_padrao_id FOREIGN KEY (motorista_padrao_id) REFERENCES motorista(id)
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
  modelo VARCHAR(30),
  porta_serial VARCHAR(10),
  baud_rate INTEGER DEFAULT 9600,
  paridade VARCHAR(30) NOT NULL DEFAULT 'NONE',
  data_bits SMALLINT DEFAULT 8,
  stop_bits SMALLINT DEFAULT 1,
  fator_multiplicacao NUMERIC(10,4) DEFAULT 1,
  casas_decimais SMALLINT DEFAULT 0,
  endereco_ip VARCHAR(200),
  simulada BOOLEAN DEFAULT FALSE NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_balanca PRIMARY KEY (id),
  CONSTRAINT ux_balanca_descricao UNIQUE (descricao),
  CONSTRAINT ck_balanca_paridade CHECK (paridade IN ('NONE', 'EVEN', 'ODD', 'MARK', 'SPACE'))
);

CREATE TABLE cancela (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(100) NOT NULL,
  modelo VARCHAR(20),
  porta_serial VARCHAR(10),
  baud_rate INTEGER DEFAULT 9600,
  paridade VARCHAR(30) NOT NULL DEFAULT 'NONE',
  data_bits SMALLINT DEFAULT 8,
  stop_bits SMALLINT DEFAULT 1,
  canal SMALLINT,
  tempo_sinal_ms INTEGER,
  endereco_ip VARCHAR(200),
  simulada BOOLEAN DEFAULT FALSE NOT NULL,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_cancela PRIMARY KEY (id),
  CONSTRAINT ux_cancela_descricao UNIQUE (descricao),
  CONSTRAINT ck_cancela_paridade CHECK (paridade IN ('NONE', 'EVEN', 'ODD', 'MARK', 'SPACE'))
);

CREATE TABLE camera (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  descricao VARCHAR(100) NOT NULL,
  modelo VARCHAR(20),
  url_imagem VARCHAR(300),
  url_video VARCHAR(300),
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_camera PRIMARY KEY (id),
  CONSTRAINT ux_camera_descricao UNIQUE (descricao)
);

CREATE TABLE ponto_controle (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  nome VARCHAR(50) NOT NULL,
  balanca_id INTEGER NOT NULL,
  camera_id INTEGER NOT NULL,
  cancela_entrada_id INTEGER NOT NULL,
  cancela_saida_id INTEGER,
  ativo BOOLEAN DEFAULT TRUE NOT NULL,
  CONSTRAINT pk_ponto_controle PRIMARY KEY (id),
  CONSTRAINT ux_ponto_controle_nome UNIQUE (nome),
  CONSTRAINT fk_ponto_controle_balanca_id FOREIGN KEY (balanca_id) REFERENCES balanca(id),
  CONSTRAINT fk_ponto_controle_camera_id FOREIGN KEY (camera_id) REFERENCES camera(id),
  CONSTRAINT fk_ponto_controle_cancela_entrada_id FOREIGN KEY (cancela_entrada_id) REFERENCES cancela(id),
  CONSTRAINT fk_ponto_controle_cancela_saida_id FOREIGN KEY (cancela_saida_id) REFERENCES cancela(id)
);

CREATE TABLE agendamento (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  veiculo_id INTEGER NOT NULL,
  motorista_id INTEGER NOT NULL,
  transportadora_id INTEGER NOT NULL,
  produto_id INTEGER NOT NULL,
  tipo_operacao VARCHAR(30) NOT NULL,
  data_prevista DATE NOT NULL,
  janela_inicio TIME,
  janela_fim TIME,
  status VARCHAR(30) NOT NULL DEFAULT 'AGENDADO',
  observacao VARCHAR(200),
  criado_por INTEGER NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_agendamento PRIMARY KEY (id),
  CONSTRAINT fk_agendamento_veiculo_id FOREIGN KEY (veiculo_id) REFERENCES veiculo(id),
  CONSTRAINT fk_agendamento_motorista_id FOREIGN KEY (motorista_id) REFERENCES motorista(id),
  CONSTRAINT fk_agendamento_transportadora_id FOREIGN KEY (transportadora_id) REFERENCES transportadora(id),
  CONSTRAINT fk_agendamento_produto_id FOREIGN KEY (produto_id) REFERENCES produto(id),
  CONSTRAINT ck_agendamento_tipo_operacao CHECK (tipo_operacao IN ('CARGA', 'DESCARGA')),
  CONSTRAINT ck_agendamento_status CHECK (status IN ('AGENDADO', 'EM_ANDAMENTO', 'CONCLUIDO', 'CANCELADO', 'EXPIRADO')),
  CONSTRAINT fk_agendamento_criado_por FOREIGN KEY (criado_por) REFERENCES usuario(id),
  CONSTRAINT ck_agendamento_janela CHECK (janela_fim IS NULL OR janela_inicio IS NULL OR janela_fim > janela_inicio)
);

CREATE TABLE pesagem (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  numero INTEGER NOT NULL,
  agendamento_id INTEGER NOT NULL,
  ponto_controle_id INTEGER NOT NULL,
  veiculo_id INTEGER NOT NULL,
  motorista_id INTEGER NOT NULL,
  placa VARCHAR(8) NOT NULL,
  tipo_operacao VARCHAR(30) NOT NULL,
  situacao VARCHAR(30) NOT NULL DEFAULT 'AUTORIZADA',
  peso_inicial_kg NUMERIC(12,3),
  peso_inicial_em TIMESTAMP,
  peso_final_kg NUMERIC(12,3),
  peso_final_em TIMESTAMP,
  peso_liquido_kg NUMERIC(12,3) GENERATED ALWAYS AS (
    CASE WHEN peso_inicial_kg IS NULL OR peso_final_kg IS NULL THEN NULL
         WHEN tipo_operacao = 'DESCARGA' THEN peso_inicial_kg - peso_final_kg
         ELSE peso_final_kg - peso_inicial_kg END) STORED,
  liberacao_manual BOOLEAN DEFAULT FALSE NOT NULL,
  liberado_por INTEGER,
  motivo_liberacao VARCHAR(500),
  motivo_cancelamento VARCHAR(200),
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_pesagem PRIMARY KEY (id),
  CONSTRAINT ux_pesagem_numero UNIQUE (numero),
  CONSTRAINT ux_pesagem_agendamento_id UNIQUE (agendamento_id),
  CONSTRAINT fk_pesagem_agendamento_id FOREIGN KEY (agendamento_id) REFERENCES agendamento(id),
  CONSTRAINT fk_pesagem_ponto_controle_id FOREIGN KEY (ponto_controle_id) REFERENCES ponto_controle(id),
  CONSTRAINT fk_pesagem_veiculo_id FOREIGN KEY (veiculo_id) REFERENCES veiculo(id),
  CONSTRAINT fk_pesagem_motorista_id FOREIGN KEY (motorista_id) REFERENCES motorista(id),
  CONSTRAINT ck_pesagem_tipo_operacao CHECK (tipo_operacao IN ('CARGA', 'DESCARGA')),
  CONSTRAINT ck_pesagem_situacao CHECK (situacao IN ('AUTORIZADA', 'PESO_INICIAL_OK', 'FINALIZADA', 'CANCELADA')),
  CONSTRAINT fk_pesagem_liberado_por FOREIGN KEY (liberado_por) REFERENCES usuario(id),
  CONSTRAINT ck_pesagem_pesos CHECK (COALESCE(peso_inicial_kg,0) >= 0 AND COALESCE(peso_final_kg,0) >= 0),
  CONSTRAINT ck_pesagem_final CHECK (situacao <> 'FINALIZADA' OR (peso_inicial_kg IS NOT NULL AND peso_final_kg IS NOT NULL)),
  CONSTRAINT ck_pesagem_manual CHECK (liberacao_manual = FALSE OR (liberado_por IS NOT NULL AND motivo_liberacao IS NOT NULL))
);

CREATE TABLE leitura_placa (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  camera_id INTEGER NOT NULL,
  agendamento_id INTEGER,
  pesagem_id INTEGER,
  placa_lida VARCHAR(10),
  confianca NUMERIC(5,2),
  resultado VARCHAR(30) NOT NULL,
  caminho_imagem VARCHAR(300),
  lida_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_leitura_placa PRIMARY KEY (id),
  CONSTRAINT fk_leitura_placa_camera_id FOREIGN KEY (camera_id) REFERENCES camera(id),
  CONSTRAINT fk_leitura_placa_agendamento_id FOREIGN KEY (agendamento_id) REFERENCES agendamento(id),
  CONSTRAINT fk_leitura_placa_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT ck_leitura_placa_resultado CHECK (resultado IN ('AUTORIZADO', 'SEM_AGENDAMENTO', 'VEICULO_NAO_CADASTRADO', 'NAO_RECONHECIDA'))
);

CREATE TABLE evento_cancela (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  cancela_id INTEGER NOT NULL,
  pesagem_id INTEGER,
  comando VARCHAR(30) NOT NULL,
  motivo VARCHAR(30) NOT NULL,
  sucesso BOOLEAN NOT NULL,
  mensagem VARCHAR(200),
  ocorrido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_evento_cancela PRIMARY KEY (id),
  CONSTRAINT fk_evento_cancela_cancela_id FOREIGN KEY (cancela_id) REFERENCES cancela(id),
  CONSTRAINT fk_evento_cancela_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT ck_evento_cancela_comando CHECK (comando IN ('ABRIR', 'FECHAR')),
  CONSTRAINT ck_evento_cancela_motivo CHECK (motivo IN ('ENTRADA', 'SAIDA', 'EMERGENCIA', 'MANUAL'))
);

CREATE TABLE log_sistema (
  id INTEGER GENERATED ALWAYS AS IDENTITY,
  pesagem_id INTEGER,
  nivel VARCHAR(30) NOT NULL,
  origem VARCHAR(30) NOT NULL,
  mensagem VARCHAR(500) NOT NULL,
  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
  CONSTRAINT pk_log_sistema PRIMARY KEY (id),
  CONSTRAINT fk_log_sistema_pesagem_id FOREIGN KEY (pesagem_id) REFERENCES pesagem(id),
  CONSTRAINT ck_log_sistema_nivel CHECK (nivel IN ('INFO', 'AVISO', 'ERRO')),
  CONSTRAINT ck_log_sistema_origem CHECK (origem IN ('LPR', 'BALANCA', 'CANCELA', 'AGENDAMENTO', 'API'))
);

-- Índices de apoio às consultas do fluxo (LPR -> agendamento -> pesagem)
CREATE INDEX ix_agendamento_veiculo_id_data_prevista ON agendamento (veiculo_id, data_prevista) WHERE status IN ('AGENDADO','EM_ANDAMENTO');
CREATE UNIQUE INDEX ux_pesagem_veiculo_aberta ON pesagem (veiculo_id) WHERE situacao IN ('AUTORIZADA','PESO_INICIAL_OK');
CREATE INDEX ix_pesagem_criado_em ON pesagem (criado_em);
CREATE INDEX ix_leitura_placa_lida_em ON leitura_placa (lida_em);
CREATE INDEX ix_evento_cancela_pesagem_id ON evento_cancela (pesagem_id);
CREATE INDEX ix_log_sistema_criado_em ON log_sistema (criado_em);
