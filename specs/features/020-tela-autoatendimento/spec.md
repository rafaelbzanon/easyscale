# Spec 020 — Tela de autoatendimento do motorista (totem)

- **Trilha:** Frontend
- **Status:** Implementada (FE-307, 2026-11-07; aprovação delegada pelo autor, revisão final pendente)
- **Data:** 2026-11-07
- **Tarefa:** FE-307 — `specs/tarefas-iniciais.md`
- **Requisitos:** RF-004, RF-029, RF-033, RN-001, RN-021, RNF-013, RNF-014
- **Decisões:** ADR-0004 §4.4 (sem login; resposta que não revela o cadastro)
- **Contratos usados:** spec 013 inteira; spec 008 §5.3 (forma da disponibilidade); spec 007 §3 (erros)
- **Casca:** spec 016 §6.3 e §8.4 (`LayoutTotem`, rota `/autoatendimento`)

---

## 1. Contexto e origem

- O motorista cria o próprio agendamento, sem login e sem operador. É a única tela sem sessão.
- O totem é uma tela de toque sem teclado físico. O leitor do código da nota age como teclado (`PRODUCT.md`). O motorista usa a tela poucas vezes, às vezes com pressa ou de luva.
- A tela nunca mostra dado do cadastro e não revela se placa ou CPF existem (RN-021, ADR-0004 §4.4 item 3).
- A criação é uma ação do motorista: a faixa só é gravada depois que ele a escolhe (RN-001, RF-029).

## 2. Objetivo

Um fluxo curto, uma pergunta por tela, com alvos grandes, que cria o agendamento pelo contrato 013 e nunca afirma sucesso sem a resposta `201`.

## 3. Fora de escopo

- Consultar, editar ou cancelar agendamento (ADR-0004 §4.4 item 5).
- Ler o código da nota por câmera (spec 013 §3). O leitor de código de barras age como teclado.
- Mostrar o modo `REAL`/`SIMULADO` ou qualquer estado do pátio (spec 016 Q-F2).
- Escolher a transportadora ou escrever observação (spec 013 P-1).

## 4. Atores

Motorista, sem sessão. A rede e o limite de tentativas são do backend.

## 5. Pré-condições

Rota `/autoatendimento`, dentro da rede liberada no backend. Fora dela, as três rotas respondem `404` ou `403` (spec 013 §6.1) e a tela mostra que o serviço não está disponível.

## 6. Comportamento normal

### 6.1 Passos

Uma pergunta por tela, com "Passo N de M" e o botão "Voltar" (menos no primeiro).

| Passo | Pergunta | Controle |
|---|---|---|
| 1 | Tipo de operação | Botões "Carga" e "Descarga". Um toque escolhe e avança. |
| 2 | Produto | Um botão por produto de `GET /api/autoatendimento/produtos` (descrição). |
| 3 | Data | Botões dos próximos 7 dias, o primeiro "Hoje" e o segundo "Amanhã". |
| 4 | Faixa de horário | Um botão por faixa de `GET /api/autoatendimento/disponibilidade?data=`, com as vagas livres. Faixa sem vaga ou encerrada fica desabilitada. A primeira com vaga leva o texto "Sugerida". O motorista toca na que quer; a tela nunca escolhe sozinha. |
| 5 | Placa | Campo grande e teclado de letras e números na tela. |
| 6 | CPF | Campo grande e teclado numérico na tela. Só dígitos; "Avançar" só com 11 dígitos. |
| 7 | Código da nota | **Só em Descarga.** Campo com foco e teclado na tela. O leitor digita o código e o Enter avança. Obrigatório (spec 013 §6.4). |
| 8 | Conferir | Resumo do que o motorista digitou e escolheu. O CPF aparece mascarado (só os dois últimos dígitos). Botões "Confirmar agendamento" e "Voltar". |

Os campos de texto usam `inputMode="none"` para o teclado do sistema não cobrir a tela; o leitor e um teclado físico continuam funcionando.

### 6.2 Confirmação

1. "Confirmar agendamento" envia `POST /api/autoatendimento/agendamentos` com `placa`, `cpf`, `tipo_operacao`, `produto_id`, `data_prevista`, `faixa_horario_id` (sempre o escolhido) e, em Descarga, `codigo_nota`. Em Carga, `codigo_nota` não vai.
2. Só com `201` aparece "Agendamento feito", com tipo, data, faixa (`faixa_hora_inicio` às `faixa_hora_fim`) e o número do agendamento da resposta. Nada além disso.
3. "Novo agendamento" volta ao passo 1 e apaga tudo.

### 6.3 Privacidade no totem

- Parada de 60 segundos sem toque, em qualquer passo, apaga os dados e volta ao passo 1. A tela de resultado volta sozinha após o mesmo tempo.
- Nada é guardado no navegador (`localStorage`, `sessionStorage`, cookie).
- A tela só usa os campos da resposta `201` (§5.1 do contrato).

## 7. Comportamento em falha

| Situação | Texto na tela | Depois |
|---|---|---|
| `422 DADOS_NAO_CONFEREM` | "Placa ou CPF não conferem. Confira os dois ou fale com o operador." Uma só mensagem, sem dizer qual. | Volta ao passo da placa, com os dados mantidos. |
| `422` em `placa` (`PLACA_INVALIDA`, `CAMPO_INVALIDO`) | "Placa inválida. Confira as letras e os números." | Passo da placa. |
| `422` em `cpf` | "CPF inválido. Confira os números." | Passo do CPF. |
| `422 CODIGO_NOTA_OBRIGATORIO` | "Informe o código da nota." | Passo da nota. |
| `422 DATA_NO_PASSADO` | "Essa data já passou. Escolha outra." | Passo da data. |
| `409 FAIXA_SEM_VAGA`, `FAIXA_ENCERRADA`, `SEM_FAIXA_DISPONIVEL` | "Essa faixa não tem mais vaga. Escolha outra." | Passo da faixa, com a disponibilidade consultada de novo. |
| `409 VEICULO_JA_AGENDADO` | "Este veículo já tem um agendamento aberto. Fale com o operador." | Fica no resumo. |
| `429 AUTOATENDIMENTO_BLOQUEADO` | "Este totem está bloqueado por um tempo. Fale com o operador." | Fica no resumo. |
| `403 REDE_NAO_PERMITIDA` ou `404` | "O autoatendimento não está disponível aqui. Fale com o operador." | Sem nova tentativa automática. |
| `500`, rede caída, corpo inválido, outro código | "Não foi possível agendar agora. Nada foi salvo. Fale com o operador." | Fica no resumo; o motorista pode tocar em "Confirmar agendamento" de novo. |
| Falha ao carregar produtos ou faixas | O mesmo texto de `403`/`404` ou "Não foi possível carregar. Tente de novo." com o botão "Tentar de novo". | — |
| Sem produto ou sem faixa com vaga | "Nenhum produto disponível. Fale com o operador." / "Sem vaga neste dia. Escolha outro dia." | — |

Nenhum texto de erro repete a mensagem do backend: os textos são fixos e não revelam cadastro.

## 8. Regras e dados

- Tipos e chamadas: `tipos/autoatendimento.ts` e `api/autoatendimento.ts`. Nenhum campo novo.
- A placa é enviada como digitada, em caixa alta; o backend normaliza (spec 007 §6.1).
- Os 7 dias e os 60 segundos são escolhas da tela, não do contrato (Q-F6).
- Alvos de toque: botões de 64 px de altura mínima, texto de 1.25rem (`DESIGN.md`). O teclado na tela segue a mesma regra.
- Textos em português, frases curtas, sem jargão.

## 9. Critérios de aceitação

| CA | Critério | Como verificar |
|---|---|---|
| CA-001 | Fluxo de Carga: tipo, produto, data, faixa, placa, CPF e confirmação enviam o `POST` com `faixa_horario_id` escolhido e sem `codigo_nota`; só com `201` aparece "Agendamento feito" com os dados da resposta. | Teste com `fetch` simulado. |
| CA-002 | Descarga tem o passo da nota, obrigatório; o Enter do leitor avança; o envio leva `codigo_nota`. | Teste. |
| CA-003 | Faixa sem vaga ou encerrada fica desabilitada; a primeira com vaga leva "Sugerida" e a tela só avança quando o motorista toca; sem vaga mostra o aviso. | Teste. |
| CA-004 | `DADOS_NAO_CONFEREM` mostra uma só mensagem, volta à placa e mantém os dados. | Teste. |
| CA-005 | Os erros da §7 mostram o texto fixo e o passo indicado; `FAIXA_SEM_VAGA` consulta a disponibilidade de novo. | Teste. |
| CA-006 | `403`, `404`, `429`, `500` e rede caída não mostram sucesso. Depois de `500`, o motorista pode confirmar de novo. | Teste. |
| CA-007 | A tela só mostra campos da resposta `201`: campos extras na resposta (ex.: nome do motorista) não aparecem. | Teste. |
| CA-008 | CPF só avança com 11 dígitos, aceita só dígitos e aparece mascarado no resumo. | Teste. |
| CA-009 | O teclado na tela escreve no campo ativo, apaga e funciona junto com o teclado físico. | Teste. |
| CA-010 | 60 segundos sem toque apagam os dados e voltam ao passo 1. | Teste com relógio simulado. |
| CA-011 | Falha ao carregar produtos ou faixas mostra erro e "Tentar de novo". | Teste. |
| CA-012 | Botões e teclas têm pelo menos 64 px de altura no navegador. | Medição no navegador, no relato. |
| CA-013 | Nenhum código grava em `localStorage`, `sessionStorage` ou `document.cookie`. | `grep`. |

## 10. Impacto

- **Pastas:** `frontend/src/paginas/totem/` (novas). `rotas.tsx` passa a usar a tela nova; `paginas/PaginaTotem.tsx` (casca da spec 016) fica sem uso e pode ser apagada pelo Loom.
- **Segurança operacional:** nenhuma ação física. A tela só pede o agendamento; a entrada continua exigindo a placa lida e o agendamento válido (RN-002). Os textos fixos e a mensagem única de `DADOS_NAO_CONFEREM` mantêm a RN-021.
- **Reversibilidade:** alta.

## 11. Perguntas em aberto

| ID | Pergunta | Tratamento |
|---|---|---|
| Q-F6 | Quantos dias à frente o motorista pode agendar, e quanto tempo de inatividade apaga a tela? O contrato não limita a antecedência (spec 008 P-7). | 7 dias e 60 segundos, só na tela. Mudar é uma constante. |
| Q-F7 | Tamanho e resolução do totem (spec 016 Q-F1). | Layout em coluna de até 48rem, testável em 1080×1920 e 1920×1080. |
| Q-F8 | O contrato não diz quanto dura o bloqueio nem quantas tentativas restam. | A tela só diz que o totem está bloqueado por um tempo. |
