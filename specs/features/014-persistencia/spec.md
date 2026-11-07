# Spec 014 — Persistência

- **Trilha:** Backend
- **Status:** Aprovada (delegada pelo autor em 2026-11-07; revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** BE-502 (spec); implementação na BE-503 — `specs/tarefas-iniciais.md`
- **Requisitos:** RNF-004, RNF-010, RNF-013, RN-006, RN-008, RN-009, RN-011, RN-013, RN-015, RN-016, RN-019, RN-020, RN-022, RN-023, RN-024
- **Decisões:** ADR-0001 (PostgreSQL), ADR-0004 (sessão e perfis), ADR-0006 (SQLAlchemy Core síncrono + Alembic)
- **Combinado com:** Gyro (spec 015, interface dos repositórios), Sextant (009), Quill (010, 012, 013), em 2026-11-07
- **Código:** `backend/src/pesagem/persistencia/`, `backend/src/pesagem/config.py`

---

## 1. Contexto e origem

- O `docs/modelo-dados/schema.sql` é referência **[PROPOSTA]** (C-002). As specs mandam, e esta spec junta as alterações já levantadas: C-002 (`AMBIENTE.md` §0.4), spec 004 §11, spec 006 §12, spec 007 §9, spec 008 §9, specs 009, 010, 012 e 013 §9, spec 015, ADR-0004 §5 e RN-022.
- As migrações do Alembic passam a ser a única fonte do esquema (ADR-0006). O `schema.sql` fica como histórico (§9).

## 2. Objetivo

Definir as tabelas, as garantias de concorrência no banco e os repositórios que a orquestração (BE-601) e a API usam.

## 3. Fora de escopo

- O que o contrato 011 (diagnóstico) acrescentar além de `leitura_placa.leituras` e `imagem_decisao`: entra numa migração seguinte (§10).
- Repositórios de cadastros, usuários e sessões: o esquema e as unicidades ficam prontos agora; as consultas entram com a tarefa de API que as usa, pelo dono de `persistencia/`.
- Backup e restauração.

## 4. Regras gerais

- Instantes em `TIMESTAMPTZ` (C-002 item 13). Pesos em `NUMERIC(12,3)`.
- Valores de situação e status em `CHECK`, com o mesmo texto dos `Enum` (`CONVENCOES.md` §4.6).
- Nomes de constraints e índices pelo `CONVENCOES.md` §6. As garantias da §6 dependem desses nomes, porque o repositório traduz a violação pelo nome.
- Nada é apagado por rota: cadastros, usuários e agendamentos só mudam de `ativo` ou de status (spec 007 P-1, spec 008 §4.1, spec 012 §4.2).

## 5. Tabelas da primeira migração (`0001_cria_tabelas_iniciais`)

Só as diferenças em relação ao `schema.sql` estão descritas; o resto continua como lá.

### 5.1 Acesso (ADR-0004, spec 012)

| Tabela | Campos e regras |
|---|---|
| `perfil` | `id`, `codigo` único. A migração cria `ADMINISTRADOR`, `OPERADOR` e `AUDITOR`. |
| `perfil_permissao` | `perfil_id`, `permissao` (texto do catálogo do código); chave (`perfil_id`, `permissao`). A migração grava a tabela do ADR-0004 §4.3. Sem `CHECK` da permissão: o catálogo fica no código (ADR-0004 §4.2). |
| `usuario` | `perfil` vira `perfil_id` (FK), e o `ck_usuario_perfil` sai. `login` único sem diferenciar maiúsculas (`ux_usuario_login` em `lower(login)`), guardado como enviado. |
| `sessao` | `id`, `usuario_id`, `hash_identificador` (SHA-256 em hexadecimal, único), `criada_em`, `ultimo_uso_em`, `encerrada_em` (vazio enquanto aberta). |
| `tentativa_acesso` | `tipo` (`LOGIN`, `AUTOATENDIMENTO`), `chave`, `falhas_seguidas`, `bloqueado_ate`; chave primária (`tipo`, `chave`). A `chave` é o SHA-256 do login em minúsculas (spec 012 §6.8) ou do endereço de origem (spec 013). Guarda o hash, e não o texto, porque o login digitado pode ser uma senha no campo errado (spec 012 §6.11). Sobrevive a reinício. |
| `registro_auditoria` | `id`, `tipo`, `responsavel_id`, `usuario_afetado_id`, `agendamento_id`, `endereco_origem`, `ocorrido_em`. `tipo` em `LOGIN_ACEITO`, `LOGIN_RECUSADO`, `LOGIN_BLOQUEADO`, `LOGOUT`, `USUARIO_CRIADO`, `USUARIO_DESATIVADO`, `USUARIO_REATIVADO`, `SENHA_REDEFINIDA`, `AGENDAMENTO_EDITADO`, `AGENDAMENTO_CANCELADO`, `AUTOATENDIMENTO_RECUSADO` (specs 008, 012, 013). Login inexistente: `usuario_afetado_id` vazio. Falha de autoatendimento: só `endereco_origem` e o instante. Sem texto livre: nada de senha, cookie, sessão ou dado digitado (RNF-013). Substitui o `log_sistema`. |

### 5.2 Cadastros (spec 007)

- `motorista`: sai o `rg` (P-2).
- `tipo_veiculo`: `descricao` única sem diferenciar maiúsculas (`lower(descricao)`).
- `veiculo`: `placa` com 7 caracteres, já normalizada; novo `chave_comparacao` (7 caracteres, **único**), calculado pelo backend com a spec 003; `transportadora_id` aceita vazio (P-5). O `formato_placa` não é guardado: sai da placa.
- `produto`, `transportadora`: como no `schema.sql`.

### 5.3 Equipamentos (C-002 itens 7 e 8, spec 004, spec 006)

O banco só cadastra; modo e comunicação vêm das variáveis de ambiente.

- `balanca`, `cancela`, `camera`: só `id`, `descricao` (única) e `ativo`. Saem `porta_serial`, `baud_rate`, `paridade`, `data_bits`, `stop_bits`, `simulada`, `endereco_ip`, `modelo`, `fator_multiplicacao`, `casas_decimais`, `canal`, `tempo_sinal_ms`, `url_imagem` e `url_video`. O protocolo da balança (spec 004 P-8) e o `endereco_ip` entram quando a Q-01 for respondida.
- `camera` ganha `ponto_controle_id` (obrigatório): o ponto tem câmeras na frente, atrás e superior (Q-06). Por isso `ponto_controle.camera_id` sai.
- `ponto_controle`: `cancela_saida_id` obrigatório (spec 006 §12); `balanca_id` único, para que a reserva por ponto (§6.2) seja a reserva da balança.

### 5.4 Agendamentos (spec 008)

- Nova tabela `faixa_horario`: `id`, `hora_inicio`, `hora_fim`, `capacidade` (> 0), `ativo`; `hora_fim > hora_inicio`.
- `agendamento`:
  - `faixa_horario_id` obrigatório; saem `janela_inicio` e `janela_fim`;
  - `transportadora_id` aceita vazio;
  - novos `origem` (`USUARIO`, `AUTOATENDIMENTO`), `codigo_nota` (até 100), `cancelado_por`, `cancelado_em`, `motivo_cancelamento` (até 200);
  - `criado_por` vazio só com `origem = AUTOATENDIMENTO`, e obrigatório com `USUARIO`;
  - `codigo_nota` só em `DESCARGA` (P-6);
  - os três campos de cancelamento são preenchidos juntos, e só com `status = CANCELADO`.

### 5.5 Operação (specs 006, 009, 010 e 015)

- `pesagem`:
  - `situacao` com os 20 valores da spec 006 §5.1, e novos `situacao_anterior`, `motivo_intervencao` (spec 006 §5.4), `versao` (≥ 1) e `classificacao` (spec 002);
  - `situacao_anterior` e `motivo_intervencao` preenchidos se, e só se, `situacao = AGUARDANDO_INTERVENCAO`;
  - `peso_liquido_kg` deixa de ser coluna gerada: o domínio calcula (spec 002) e grava, e o `ck_pesagem_peso_liquido` confere a fórmula da RN-006. Assim, o banco recusa um líquido que não bate com os pesos;
  - `classificacao` preenchida se, e só se, `peso_liquido_kg` estiver;
  - novo `situacao_desde`: instante da última transição, para a fila da balança por ordem de chegada e para os tempos-limite valerem depois de um reinício (spec 015);
  - novo `aguarda_liberacao_balanca`: a operação foi cancelada com o caminhão na balança (spec 006 §6.4, spec 009 §6.6); só com `situacao = CANCELADA`;
  - `placa`, `chave_comparacao`, `veiculo_id`, `motorista_id` e `tipo_operacao` são cópia do agendamento e do veículo no momento da criação, de propósito (C-002 item 15): o histórico mostra o que valia na hora, e o filtro por placa usa a `chave_comparacao` copiada (spec 010);
  - saem `numero` (nenhum requisito o usa; o `id` identifica a pesagem), `liberado_por`, `motivo_liberacao` e o `ck_pesagem_manual`: responsável e motivo de cada ação manual ficam no `evento_operacao`, e `liberacao_manual` continua na pesagem.
- Nova tabela `evento_operacao`: o histórico da pesagem numa só lista, na ordem (`ocorrido_em`, `id`) (spec 006 §10, spec 010, RNF-010). Substitui o `evento_cancela`.
  - `tipo_registro`: `TRANSICAO`, `TRANSICAO_REJEITADA`, `EVENTO_REGISTRADO` ou `COMANDO_CANCELA`;
  - `evento` (valor de `TipoEvento`, `TipoAcaoManual`, `PESO_ACEITO`, `CRIACAO`, ou comando e cancela, como `ABRIR_SAIDA`), `situacao_origem` (vazia só na `CRIACAO`), `situacao_destino` (só em `TRANSICAO`), `motivo_rejeicao` (só em `TRANSICAO_REJEITADA`), `motivo_intervencao`, `motivo_dispositivo`;
  - `peso_kg`, `peso_liquido_kg`, `classificacao`: o peso aceito, ou o final descartado por `TENTAR_NOVAMENTE` com `LIQUIDO_NEGATIVO` (spec 006 §6.1);
  - `cancela` (`ENTRADA`, `SAIDA`), `comando` (`ABRIR`, `FECHAR`), `resultado` (`CONFIRMADO`, `FALHA`, `SEM_CONFIRMACAO`) e `tentativas` (≥ 1), todos só em `COMANDO_CANCELA` (spec 004 §11, C-002 item 5);
  - `responsavel_id` e `motivo` (até 200), preenchidos juntos: ações manuais, liberação manual de entrada e liberação do caminhão cancelado (RN-011, RN-016, RN-020);
  - `leitura_placa_id`, `imagem_id`; sem placa nem CPF (RNF-013).
- Nova tabela `liberacao_caminhao` (spec 009 §5.6): uma linha por pesagem (`pesagem_id` é a chave), criada em `PENDENTE` quando a operação é cancelada com o caminhão na balança. `etapa` em `PENDENTE`, `ABRINDO_SAIDA`, `AGUARDANDO_BALANCA_VAZIA`, `FECHANDO_SAIDA`, `CONCLUIDA`, `FALHOU`; `motivo_falha` só em `FALHOU`; `pedido_por`, `motivo`, `pedida_em` vazios só em `PENDENTE`; `atualizada_em`. Cada tentativa nova reaproveita a linha, e os comandos ficam no `evento_operacao`.
- Nova tabela `leitura_placa` (spec 009 §5.2, spec 015): `pesagem_id` (preenchido na autorização, na volta ou na liberação manual de entrada), `agendamento_id`, `imagem_id`, `origem`, `capturada_em`, `decidida_em`, `decisao` (`AUTORIZADA`, `RETORNO_ACEITO`, `NAO_AUTORIZADA`), `motivo` (os 13 da spec 009 §5.3, só em `NAO_AUTORIZADA`), `placa_lida`, `placa_normalizada`, `formato`, `correcoes` (JSON), `confianca` (0 a 1, 3 casas) e `leituras` (JSON com ROIs, textos e confianças, para o diagnóstico). Índice em (`decidida_em`, `id`) para achar a mais recente. Substitui a `leitura_placa` do `schema.sql`.
- Nova tabela `imagem_decisao` (RN-022, §10): `conteudo` (`bytea`), `origem`, `capturada_em`, ROI opcional (`roi_x`, `roi_y`, `roi_largura`, `roi_altura`, todos ou nenhum) e os campos de exclusão `excluida_por`, `excluida_em`, `motivo_exclusao`, preenchidos se, e só se, `conteudo` estiver vazio.

## 6. Garantias de concorrência

Todas valem com o isolamento padrão do PostgreSQL (`READ COMMITTED`).

| Regra | Como o banco garante | Erro do repositório |
|---|---|---|
| `versao` da operação (spec 006 §7.3) | `UPDATE ... WHERE id = :id AND versao = :versao_lida`. Nenhuma linha alterada: alguém gravou antes. | `ErroConflitoVersao` |
| Reserva única da balança (RN-019, spec 006 §6.3) | Índice único parcial `ux_pesagem_balanca_reservada` em `ponto_controle_id`, nas 14 situações de `AUTORIZADA` a `FECHANDO_SAIDA_INICIAL` e de `RETORNO_AUTORIZADO` a `FECHANDO_SAIDA`, e em `AGUARDANDO_INTERVENCAO` com `situacao_anterior` numa delas. | `ErroBalancaOcupada` |
| Uma operação aberta por placa (RN-008) | Índice único parcial `ux_pesagem_veiculo_aberta` em `veiculo_id`, fora de `FINALIZADA` e `CANCELADA`. | `ErroOperacaoAberta` |
| Nova pesagem só depois de `CANCELADA` (RN-009) | Índice único parcial `ux_pesagem_agendamento_id` em `agendamento_id`, fora de `CANCELADA`. | `ErroOperacaoAberta` |
| Um agendamento aberto por veículo (RN-023) | Índice único parcial `ux_agendamento_veiculo_aberto` em `veiculo_id`, com `AGENDADO` ou `EM_ANDAMENTO`. Antes de inserir, a mesma transação grava `EXPIRADO` nos `AGENDADO` do veículo com data passada (spec 008 §9). | `ErroVeiculoJaAgendado` |
| Vaga da faixa (RN-015) | A criação trava as faixas com `SELECT ... FOR UPDATE`, sempre na ordem de `hora_inicio`, conta e insere na mesma transação. Pedidos pela mesma faixa ficam em fila. | `ErroFaixaSemVaga`, `ErroFaixaEncerrada`, `ErroSemFaixaDisponivel` |
| Faixas ativas não se sobrepõem (spec 008 §6.7) | Restrição `EXCLUDE` com `tsrange` sobre os horários, só entre faixas ativas. Limites `[início, fim)`, então faixas vizinhas são aceitas. | `ErroFaixaSobreposta` |
| Uma leitura gera no máximo uma pesagem (spec 009 §6.5) | Ligar a leitura é `UPDATE ... WHERE pesagem_id IS NULL`. O segundo pedido espera o bloqueio da linha e não a acha mais livre. | `ErroLeituraJaUsada` |
| Um pedido de liberação do caminhão cancelado por vez (spec 009 §6.6) | `UPDATE ... WHERE etapa IN ('PENDENTE', 'FALHOU')`. | `ErroLiberacaoIndisponivel` |
| Cancelamento e entrada ao mesmo tempo (spec 008 §6.9) | A criação da operação e o cancelamento só alteram o agendamento com `status = AGENDADO` na condição do `UPDATE`. Quem chega depois não altera nada. | `ErroStatusAgendamento` |
| Unicidades de cadastro (spec 007 §6.4, spec 012) | `ux_` de CPF, CNPJ, `chave_comparacao`, `lower(login)` e `lower(descricao)`. | `ErroDuplicidade`, com o nome da restrição |

Nenhuma transação fica aberta durante um comando físico ou uma leitura de dispositivo: a situação é gravada e confirmada **antes** do comando (spec 006 §7.2).

## 7. Repositórios

Síncronos (ADR-0006). Quem está num laço assíncrono chama com `asyncio.to_thread`. Um arquivo por agregado (`CONVENCOES.md` §2). Interface combinada com o Gyro (spec 015).

- `banco.py`: `criar_engine(configuracao)` e `transacao(engine)`, que dá um `Transacao` com `pesagens`, `agendamentos`, `veiculos`, `leituras_placa`, `imagens`, `pontos_controle` e `conexao`, todos na mesma transação. Confirma ao sair sem erro e desfaz se houver exceção. Os repositórios não fazem `commit`.
- As violações de restrição viram os erros da §6 **ao sair** do bloco: o PostgreSQL aborta a transação, e não há como seguir nela. `ErroConflitoVersao`, `ErroStatusAgendamento`, `ErroLeituraJaUsada` e os erros de faixa saem na hora.
- Toda gravação recebe o instante (`em`) de quem chama, e as regras do dia recebem `hoje` no fuso do pátio. O repositório não lê relógio.

### 7.1 `repositorios/pesagem.py`

| Função | Efeito |
|---|---|
| `criar_operacao(agendamento_id, ponto_controle_id, em, leitura_placa_id, liberacao_manual, responsavel_id, motivo)` | Muda o agendamento de `AGENDADO` para `EM_ANDAMENTO`, insere a pesagem com as cópias da §5.5, liga a leitura e grava o evento `CRIACAO`. |
| `obter_operacao(pesagem_id)` | A `Operacao` do domínio com ids, `situacao_desde` e `aguarda_liberacao_balanca`. |
| `listar_operacoes_abertas()` | Fora de `FINALIZADA` e `CANCELADA`, por `situacao_desde`: retomada e fila (spec 006 §6.3, §7.2). |
| `buscar_operacao_aberta_por_veiculo(veiculo_id)` | RN-018. |
| `gravar_transicao(pesagem_id, versao_lida, operacao_nova, evento, responsavel_id, hoje, em, aguarda_liberacao_balanca, leitura_placa_id, imagem_id)` | Grava com a `versao` da §6 e o evento `TRANSICAO`. `FINALIZADA` leva o agendamento a `CONCLUIDO`; `CANCELADA`, a `AGENDADO` se `data_prevista` ainda não passou, ou a `EXPIRADO` (spec 006 §6.2, spec 008 §6.6). Com `aguarda_liberacao_balanca`, cria a `liberacao_caminhao` em `PENDENTE`. |
| `registrar_evento(pesagem_id, resultado, responsavel_id, em, motivo_dispositivo, leitura_placa_id, imagem_id)` | `TransicaoRejeitada` ou `EventoRegistrado` do domínio (RN-010). |
| `registrar_comando_cancela(pesagem_id, cancela, comando, resultado, tentativas, em, responsavel_id, motivo)` | Comando e resultado (spec 004). |
| `listar_aguardando_liberacao_balanca()`, `buscar_liberacao_caminhao(pesagem_id)`, `pedir_liberacao_caminhao(pesagem_id, pedido_por, motivo, em)`, `atualizar_liberacao_caminhao(pesagem_id, etapa, em, motivo_falha)` | Liberação do caminhão cancelado (RN-020). Em `CONCLUIDA`, `aguarda_liberacao_balanca` volta a falso. |

### 7.2 Demais repositórios

| Função | Efeito |
|---|---|
| `agendamentos.criar_agendamento(dados, hoje, hora_atual)` | Aplica a §6 (expiração, vaga, faixa) e insere. Sem `faixa_horario_id`, usa a primeira faixa ativa, não encerrada e com vaga (spec 008 §6.3). Devolve o id e a faixa usada. |
| `agendamentos.cancelar_agendamento(agendamento_id, responsavel_id, motivo, hoje, em)` | Só de `AGENDADO` ainda no dia ou depois; grava os campos de cancelamento e o `registro_auditoria`. |
| `veiculos.buscar_situacao_por_chave(chave_comparacao)` | Retrato para a RN-002: veículo e `ativo`, operação aberta, e os agendamentos abertos com `faixa_hora_inicio` e `motorista_ativo`. A orquestração decide. |
| `leituras_placa.registrar(leitura)`, `leituras_placa.buscar(leitura_placa_id)` | Grava a leitura e a decisão; a busca serve para a liberação manual de entrada conferir a leitura (RN-016). |
| `imagens.salvar(conteudo, origem, capturada_em, roi)` | Grava a imagem da decisão e devolve o id. |
| `pontos_controle.obter_unico()` | O único ponto ativo; zero ou mais de um é erro, porque o sistema não escolhe sozinho (RF-030). |

A validação das referências (ativo, existente) e dos campos fica na API (spec 008 §6.8). Os repositórios de cadastros, usuários, sessões e tentativas entram com a tarefa de API que os usa.

## 8. Configuração (`config.py`)

| Variável | Conteúdo |
|---|---|
| `PESAGEM_BANCO_HOST` | Host do PostgreSQL. |
| `PESAGEM_BANCO_PORTA` | Porta, inteiro de 1 a 65535. |
| `PESAGEM_BANCO_NOME` | Nome do banco. |
| `PESAGEM_BANCO_USUARIO` | Usuário. |
| `PESAGEM_BANCO_SENHA` | Senha. Nunca aparece em log nem em mensagem de erro. |

Todas obrigatórias, sem valor padrão. Se faltar uma ou houver valor inválido, a leitura falha com `ErroConfiguracao`, que cita o nome da variável e nunca o valor, e o backend não inicia (`AMBIENTE.md` §8).

## 9. Comportamento em falha

| Situação | Resultado |
|---|---|
| Banco indisponível ou queda no meio da transação | A transação é desfeita, nada fica pela metade, e o erro sobe como `ErroBancoIndisponivel`. A orquestração não emite o comando físico (spec 006 §7.3). |
| Violação de restrição conhecida | Erro próprio da §6; a transação é desfeita. |
| Violação de restrição não prevista | Sobe como `ErroPersistencia`, sem detalhe do driver para fora de `persistencia/`; a transação é desfeita. |
| Banco sem a migração mais recente | Os testes aplicam `alembic upgrade head`. Conferir na partida fica com a BE-801. |

## 10. Imagens e migrações seguintes

As imagens das decisões ficam **no banco**, em `bytea`, numa tabela própria, gravadas na mesma transação da decisão (D-13, RN-022). Motivo: imagem e decisão nunca ficam uma sem a outra, e o backup é um só. O volume é pequeno, porque só as imagens das decisões são guardadas. A exclusão pedida pelo administrador apaga só os bytes e registra o responsável e o motivo.

Cada contrato ou spec que precise de mais dados gera uma migração nova, pelo dono de `persistencia/`. Já se sabe que pode vir: o que o contrato 011 acrescentar.

## 11. Critérios de aceitação

Todos verificados contra PostgreSQL 18.6 em contêiner (ADR-0006).

| CA | Critério |
|---|---|
| CA-001 | `alembic upgrade head` cria o esquema num banco vazio, e `alembic downgrade base` o remove. |
| CA-002 | Os perfis e as permissões do ADR-0004 §4.3 existem depois da migração. |
| CA-003 | Duas gravações da mesma operação com a mesma `versao_lida`: uma grava, a outra recebe `ErroConflitoVersao`, e a operação fica com a primeira. |
| CA-004 | Com uma operação reservando a balança, outra que passa a `AUTORIZADA` ou `RETORNO_AUTORIZADO` no mesmo ponto recebe `ErroBalancaOcupada`; em `AGUARDANDO_INTERVENCAO` vinda de uma situação que reserva, a reserva continua; em `EM_CARGA_DESCARGA`, a balança fica livre. |
| CA-005 | Uma segunda operação aberta para o mesmo veículo recebe `ErroOperacaoAberta`; depois de `FINALIZADA` ou `CANCELADA`, é aceita. |
| CA-006 | Uma segunda pesagem para o mesmo agendamento só é aceita se a anterior estiver `CANCELADA` (RN-009). |
| CA-007 | Dois pedidos simultâneos pela última vaga da faixa: um cria, o outro recebe `ErroFaixaSemVaga`. Cancelar libera a vaga; `CONCLUIDO` não libera. |
| CA-008 | Com um agendamento aberto, um segundo para o mesmo veículo recebe `ErroVeiculoJaAgendado`, inclusive com dois pedidos simultâneos; um `AGENDADO` de data passada vira `EXPIRADO` e não impede. |
| CA-009 | Sem `faixa_horario_id`, a criação usa a primeira faixa ativa, não encerrada e com vaga; sem nenhuma, `ErroSemFaixaDisponivel` e nada é criado. Faixa escolhida já encerrada: `ErroFaixaEncerrada`. |
| CA-010 | Faixas ativas sobrepostas recebem `ErroFaixaSobreposta`; vizinhas e inativas são aceitas. |
| CA-011 | Cancelar um agendamento `EM_ANDAMENTO` ou vencido recebe `ErroStatusAgendamento`; criar operação para um agendamento já cancelado também. |
| CA-012 | `gravar_transicao` para `FINALIZADA` muda o agendamento para `CONCLUIDO`; para `CANCELADA`, para `AGENDADO` no mesmo dia e `EXPIRADO` depois dele. Tudo na mesma transação que a operação. |
| CA-013 | O banco recusa `peso_liquido_kg` que não bate com a RN-006, situação fora da lista e `AGUARDANDO_INTERVENCAO` sem `situacao_anterior` ou sem motivo. |
| CA-014 | Uma exceção dentro de `transacao()` desfaz tudo o que foi gravado nela. |
| CA-015 | CPF, CNPJ, `chave_comparacao` e login repetidos (este sem diferenciar maiúsculas) são recusados com `ErroDuplicidade`. |
| CA-016 | `config.py` falha com `ErroConfiguracao` citando a variável que falta ou é inválida, sem mostrar o valor. |
| CA-017 | Só `persistencia/` importa `sqlalchemy`, `psycopg` e `alembic` (teste de camadas). |
| CA-018 | Uma leitura de placa gera no máximo uma pesagem: o segundo pedido recebe `ErroLeituraJaUsada`. |
| CA-019 | A liberação do caminhão cancelado nasce em `PENDENTE`, aceita um pedido por vez (`ErroLiberacaoIndisponivel`) e, em `CONCLUIDA`, solta a balança. |
| CA-020 | O histórico guarda, no evento de `TENTAR_NOVAMENTE`, o peso final, o líquido e a classificação descartados. |
| CA-021 | O retrato do veículo traz a operação aberta e os agendamentos abertos; placa desconhecida dá `None`. |

## 12. Impacto

- **Código:** `persistencia/` (`banco.py`, `erros.py`, `repositorios/`, `migracoes/`), `config.py`, `tests/integracao/persistencia/`. Dependências de execução no `pyproject.toml` (ADR-0006). A `persistencia/` importa tipos do `dominio/` (`Operacao` e eventos), sem regra.
- **`schema.sql`:** vira histórico. Recebe só um aviso no topo, apontando para as migrações; não é mais atualizado (P-10).
- **Orquestração (BE-601):** usa a §7 e trata os erros da §6. A checagem de câmeras e cancelas antes de `BALANCA_DISPONIVEL` (spec 006 §6.3) continua dela; o banco só impede duas reservas.
- **API (BE-701 a BE-707):** traduz os erros da §6 para `409` e as validações para `422`.
- **`CONVENCOES.md`:** §2 ganha `persistencia/migracoes/` e `tests/integracao/persistencia/`; §6 deixa de ter migrações pendentes e ganha o prefixo `ex_` para restrição `EXCLUDE`; P-4 ganha `persistencia` → `dominio` (só tipos).
- **Segurança operacional:** nenhuma ação física. A reserva da balança e a unicidade por placa saem do código e passam a ser garantidas também pelo banco.
- **Reversibilidade:** alta enquanto não houver dados reais; `downgrade` desfaz a migração.

## 13. Perguntas em aberto

| ID | Pergunta | Tratamento até a resposta |
|---|---|---|
| P-1 | O `numero` da pesagem do banco legado precisa voltar para algum documento (Q-03)? | Fora; o `id` identifica a pesagem. |
| P-2 | Protocolo da balança e `endereco_ip` no cadastro (Q-01, spec 004 P-8). | Fora até a Q-01. |
