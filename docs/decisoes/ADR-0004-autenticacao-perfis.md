# ADR-0004 — Autenticação, sessão e perfis

- **Trilha:** Contrato
- **Status:** Aceita
- **Data:** 2026-11-04
- **Decisão relacionada:** D-04 — `AMBIENTE.md` §10.2, §15
- **Tarefa:** CT-001 (`specs/tarefas-iniciais.md`)
- **Requisitos:** RF-024, RF-031, RF-032, RF-033, RN-001, RN-011, RN-013, RN-016, RN-020, RN-021, RN-022, RNF-013, RNF-014
- **Aprovação:** autor, 2026-11-04 (respostas às perguntas da §6 e escolha da opção A, recomendada)

---

## 1. Contexto

- Fatos que já valem:
  - perfis iniciais `ADMINISTRADOR`, `OPERADOR` (acompanha e solicita ações) e `AUDITOR` (só consulta), com mais usuários e novos perfis possíveis (Q-11, RF-031);
  - só o administrador edita e cancela agendamentos e faz liberação manual (RN-013, RN-016);
  - toda intervenção registra o responsável, que precisa ser um usuário identificado (RN-011);
  - a spec 006 §9 define quem pede cada ação da operação;
  - segurança é decidida no backend; a interface só apresenta e solicita (RNF-014, S-5).
- O sistema é um monólito com um único serviço de backend e PostgreSQL (ADR-0001, ADR-0002), usado por poucas pessoas numa rede local (Q-12 em aberto, Q-07 em aberto).
- O `docs/modelo-dados/schema.sql` já tem `usuario` com `login`, `senha_hash`, `perfil` e `ativo`, mas com só dois perfis fixos em um `CHECK` (C-002 item 9).

## 2. Critérios

1. Corte imediato de acesso: um usuário desativado perde o acesso na hora, porque o sistema aciona equipamento físico.
2. Responsável confiável nos registros de auditoria.
3. Novos perfis sem mudar a regra de negócio (RF-031).
4. Simplicidade para um protótipo de TCC, com poucas peças e poucas dependências (`AGENTS.md` §10.1).
5. Funciona na atualização em tempo real, seja qual for a escolha da CT-002.

## 3. Opções de autenticação

| Opção | Como funciona | Prós | Contras |
|---|---|---|---|
| **A. Sessão guardada no banco, com cookie** | O login cria uma sessão no PostgreSQL. O navegador guarda o identificador em cookie `HttpOnly`. | Corte imediato; JavaScript não lê o cookie, o que reduz o roubo por XSS; o navegador envia o cookie sozinho, inclusive em WebSocket e SSE; sem dependência nova. | Uma consulta ao banco por requisição (irrelevante nesta escala); exige proteção contra CSRF. |
| **B. Token JWT** | O login devolve um token assinado, validado sem consultar o banco. | Sem estado; bom para vários serviços. | O corte imediato exige uma lista de revogação, o que anula a vantagem; exige gerenciar chave de assinatura e nova dependência; guardado em JavaScript, fica exposto a XSS. Nosso cenário é um único serviço. |
| **C. Provedor externo (OIDC)** | Um serviço à parte cuida de login e usuários. | Recursos prontos (MFA, recuperação de senha). | Mais um serviço para rodar e documentar; desproporcional ao protótipo. |
| **D. Sem autenticação** | Qualquer um na rede usa o sistema. | Nada a fazer. | Contraria RN-011, RN-013 e RN-016. Descartada. |

## 4. Decisão

### 4.1 Autenticação: opção A

1. **Sessão:** o identificador é aleatório, gerado com `secrets`. O banco guarda só o hash dele, para que um vazamento da tabela não permita assumir sessões.
2. **Cookie:** `HttpOnly` e `SameSite=Strict`. `Secure` é obrigatório, porque a demonstração usa HTTPS (P-D). A forma de fornecer o HTTPS fica para a INT-001.
3. **CSRF:** o `SameSite=Strict` é a defesa principal; a API também só aceita mudanças de estado em JSON e confere a origem contra a lista configurada.
4. **Fim da sessão:** logout, tempo sem uso ou usuário desativado. Os tempos vêm de configuração, sem valor padrão inventado.
5. **Senha:** guardada com `hashlib.scrypt`, da biblioteca padrão, sem dependência nova, e com sal por usuário. Os parâmetros ficam gravados junto com o hash, para poderem subir no futuro; os valores serão fixados na spec, com justificativa.
6. **Tentativas de login:** limitadas por `login`, com limite vindo de configuração. A mensagem de erro não revela se o `login` existe. Login e falhas vão para a auditoria, sem nunca registrar a senha.
7. **Primeiro administrador:** criado por comando explícito na instalação, que pede a senha. Nenhuma senha padrão fica no código ou no repositório.

A queda de uma sessão não afeta a operação física: a máquina de estados continua, e só as ações manuais ficam indisponíveis até um novo login.

### 4.2 Permissões: catálogo no código, perfis nos dados

Para atender ao RF-031:
- cada rota declara **uma permissão**, e o catálogo de permissões fica no código, porque cada uma corresponde a uma funcionalidade;
- os **perfis são dados**: a relação perfil → permissões fica no banco, então um novo perfil não exige mudar as rotas;
- cada usuário tem **um** perfil;
- o backend verifica a permissão em toda rota. A interface recebe as permissões do usuário só para esconder o que ele não pode usar.

Por enquanto, os perfis são criados por migração. Uma tela para isso fica para quando houver necessidade (P-A).

O `AUDITOR` só consulta (Q-11), então não recebe `CRIAR_AGENDAMENTO`.

### 4.3 Permissões iniciais

| Permissão | Cobre | `ADMINISTRADOR` | `OPERADOR` | `AUDITOR` |
|---|---|---|---|---|
| `CONSULTAR_OPERACAO` | Tela operacional, histórico e estado dos dispositivos | ✓ | ✓ | ✓ |
| `CONSULTAR_IMAGENS_DECISAO` | Imagens salvas das decisões, com ROIs e leituras (Q-08) | ✓ | ✓ | ✓ |
| `CONSULTAR_IMAGENS_TEMPO_REAL` | Imagem atual das câmeras no diagnóstico (Q-08) | ✓ | ✓ | — |
| `EXCLUIR_IMAGENS_DECISAO` | Excluir imagens salvas, com motivo registrado (RN-022) | ✓ | — | — |
| `TENTAR_NOVAMENTE` | Spec 006 §9 | ✓ | ✓ | — |
| `LIBERAR_CAMINHAO_CANCELADO` | RN-020 | ✓ | ✓ | — |
| `INTERVIR_OPERACAO` | Confirmações manuais, liberação de retorno, aceite de peso e cancelamento (RN-016, spec 006 §9) | ✓ | — | — |
| `CRIAR_AGENDAMENTO` | Criar pela tela interna (RN-001) | ✓ | ✓ | — |
| `CONSULTAR_AGENDAMENTOS` | Consultar agendamentos, sem CPF (spec 008) | ✓ | ✓ | ✓ |
| `GERENCIAR_AGENDAMENTOS` | Editar e cancelar (RN-013) | ✓ | — | — |
| `CONSULTAR_CADASTROS` | Consultar os cadastros; só com `GERENCIAR_CADASTROS` o CPF vem completo (spec 007) | ✓ | ✓ | — |
| `GERENCIAR_CADASTROS` | Veículos, motoristas, transportadoras, produtos, tipos de veículo e faixas (RF-028) | ✓ | — | — |
| `GERENCIAR_USUARIOS` | Criar e desativar usuários, trocar senha (RF-032) | ✓ | — | — |
| `CONTROLAR_SIMULADORES` | Trocar cenários e simular chegadas, só com todos os dispositivos em `SIMULADO` (spec 011 §6.4; acrescentada em 2026-11-07, aprovação delegada) | ✓ | — | — |

O `AUDITOR` acompanha os processos e vê as imagens das decisões, mas não as imagens em tempo real (Q-08, 2026-11-04).

### 4.4 Autoatendimento do motorista, sem login (RF-033, RN-021)

A rota de autoatendimento é a **única exceção** à exigência de sessão, e tem estas barreiras:
1. **Rede:** só aceita requisições de um totem ou da rede do pátio. A lista de redes vem de configuração, sem valor padrão: sem configuração, a rota fica desligada.
2. **Cadastro:** a placa e o CPF precisam corresponder a um veículo e a um motorista já cadastrados. Assim, a tela não permite que alguém sem cadastro abra a cancela (RN-002).
3. **Dados:** a resposta não revela se a placa ou o CPF existem nem devolve dados do cadastro (RNF-013).
4. **Abuso:** tentativas limitadas por origem, com limite vindo de configuração, e as regras de faixa continuam valendo (RN-014, RN-015).
5. **Alcance:** a rota só cria agendamento. Editar, cancelar e consultar seguem com as permissões da §4.3.

**Risco aceito:** quem conhece a placa e o CPF de um motorista pode agendar por ele, e o CPF não é segredo. Isso só é aceitável com o acesso limitado ao pátio; levar a tela para a internet exige um novo ADR. O código da nota também não prova que a nota é verdadeira, porque não há consulta externa.

## 5. Consequências

- **Requisitos novos:** RF-032 (gestão de usuários), RF-033 (autoatendimento) e RN-021.
- **Tarefas novas:** CT-106 (`contrato-api-autenticacao`), CT-107 (`contrato-api-autoatendimento`) e FE-307 (tela do motorista).
- **Contratos CT-101 a CT-105:** cada rota indica sua permissão, e toda rota protegida responde `401` sem sessão válida e `403` sem permissão.
- **Esquema (BE-502), sem alterar agora:**
  - tabelas de `sessao`, `perfil` e `perfil_permissao`;
  - `agendamento.criado_por` hoje é obrigatório e precisa aceitar a origem autoatendimento;
  - um campo para `codigo_nota` no agendamento;
  - `usuario.perfil` passa a referenciar `perfil`, e o `ck_usuario_perfil` sai;
  - auditoria de login e registros de ação com o usuário responsável (C-002 item 12).
- **Backend:** a verificação fica em `api/`, fora do domínio, como previsto na spec 006 §9. Nenhuma dependência nova para autenticar.
- **Frontend:** não guarda credencial em JavaScript. Trata `401` voltando ao login, e `403` mostrando que falta permissão.
- **Tempo real (CT-002):** o cookie é enviado no início da conexão, tanto em SSE quanto em WebSocket; em WebSocket, a origem precisa ser conferida.
- **Limites conhecidos:** sem MFA nem recuperação de senha por e-mail; o administrador redefine a senha.
- **Reversibilidade:** média. Trocar a forma de autenticar afeta o login e o frontend, mas não as rotas nem as permissões.

## 6. Perguntas para aprovação

| ID | Pergunta | Recomendação |
|---|---|---|
| P-A | Novos perfis por migração agora, com tela depois? | Sim. Você disse "por enquanto apenas esses", e a estrutura já permite crescer. |
| P-B | Criar agendamento é só do administrador? | Superada pela resposta abaixo. |
| P-C | Criar o RF-032 e a CT-106? | Sim. Sem eles, não há como cadastrar usuários. |
| P-D | Haverá HTTPS na demonstração? | Definir com a Q-07. O ADR funciona nos dois casos, mas sem HTTPS a limitação fica documentada. |

**Respostas do autor (2026-11-04):**

- **P-A:** sim.
- **P-B:** agendamentos podem ser feitos por qualquer pessoa, inclusive o motorista, por uma tela própria, sem operador nem administrador. Essa tela também serve para ler a nota de descarga ou agendar carga. Confirmado depois: acesso por totem ou rede do pátio; só veículo e motorista cadastrados, com placa e CPF; o motorista digita ou escaneia o código da nota.
- **P-C:** a critério do agente: criar o RF-032 e a CT-106.
- **P-D:** haverá HTTPS na demonstração.

