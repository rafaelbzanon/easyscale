# AGENTS.md — Guia para agentes de IA (OpenCode)

Sistema open-source de automação de pesagem rodoviária com LPR e visão computacional (TCC — IFRS, Veranópolis).

Este arquivo define **como** o agente deve trabalhar neste repositório. O **o quê** e o **com quê** estão em `AMBIENTE.md` (referência técnica) e nas especificações em `specs/` (quando existirem).

> Leia este arquivo e o `AMBIENTE.md` no início de toda sessão de trabalho.

---

## 0. Legenda de status (usada neste arquivo e no `AMBIENTE.md`)

| Marca | Significado |
|---|---|
| **[ARTIGO]** | Requisito ou informação descrita no artigo do TCC. |
| **[DEFINIDO]** | Decisão já tomada pelo autor do projeto (tecnologias fixas). Não alterar. |
| **[PROPOSTA]** | Sugestão técnica ainda **não aprovada**. Não tratar como fato nem como decisão. |
| **[PENDENTE]** | Decisão em aberto. Exige discussão e aprovação explícita do autor. |

Regra: nunca promova uma **[PROPOSTA]** a **[DEFINIDO]** por conta própria. Só o autor aprova.

---

## 1. Estado atual do projeto

- O desenvolvimento **está em andamento**. O backend já tem as regras de domínio, a camada de dispositivos com simuladores, o pipeline de LPR e testes automatizados, em `backend/`.
- **Ainda não existem** API HTTP, banco de dados em execução, migrations, frontend nem Dockerfiles. O `docs/modelo-dados/schema.sql` é só referência **[PROPOSTA]**.
- O andamento fica em `specs/tarefas-iniciais.md` e o estado de cada spec em `specs/README.md`.
- **Não presuma** que qualquer módulo, comando ou arquivo de configuração exista. Verifique no repositório antes de citar ou usar.
- A organização real do código segue o `CONVENCOES.md`. O que ainda não foi criado continua sendo plano, não um retrato do código.
- Se este arquivo ficar desatualizado em relação ao repositório, avise o autor e proponha a correção; não "conserte" a realidade para combinar com o documento.

## 2. Contexto resumido

Sistema para automatizar as etapas **posteriores ao agendamento manual** de uma operação de pesagem rodoviária de caminhões **[ARTIGO]**:

1. Usuário com permissão, ou o motorista no autoatendimento, cria o agendamento manualmente (**o agendamento não é automatizado**; RF-033, ADR-0004).
2. Câmeras + LPR identificam o caminhão.
3. O sistema valida a placa e verifica se há agendamento correspondente.
4. O sistema controla as cancelas e identifica a posição do caminhão na balança pela câmera superior, podendo combinar todas as câmeras; a orientação do motorista está fora do protótipo (Q-05, Q-17).
5. O sistema realiza e registra as pesagens necessárias.
6. Após carga/descarga, realiza a pesagem final, calcula o peso líquido e guarda o histórico.

Também haverá interface de acompanhamento e administração que mostre imagens das câmeras, **ROIs** usadas pela visão computacional e as **interpretações do algoritmo**, para inspeção e diagnóstico.

O artigo descreve um **protótipo funcional**, validado em ambiente controlado (imagens de placas e simulação serial da balança e das cancelas). Mantenha o escopo compatível com isso.

## 3. Tecnologias

**[DEFINIDO] — não substituir:**

- Backend: Python + FastAPI
- Frontend: TypeScript + Tailwind CSS
- Infraestrutura de desenvolvimento e execução: Docker
- Visão computacional: OpenCV
- Reconhecimento de placas: EasyOCR (tecnologia inicialmente prevista)
- Comunicação com equipamentos: PySerial (RS232) para balança e dispositivos de controle das cancelas

**Decisões aprovadas em ADR** (`docs/decisoes/`):

- Banco de dados: PostgreSQL (ADR-0001)
- Arquitetura: monólito modular (ADR-0002)
- Ferramentas do backend: pytest, pytest-cov, ruff e mypy (ADR-0003)
- Autenticação e permissões: sessão no banco com cookie; permissões no código e perfis no banco (ADR-0004)
- Atualização em tempo real: SSE para eventos e imagens sob demanda (ADR-0005)

**[PENDENTE] — não escolher sozinho, não instalar, não "assumir por padrão":**

- Framework do frontend
- ORM e ferramenta de migração
- Protocolos detalhados da balança e das cancelas
- Ferramentas de teste, lint, formatação e tipagem estática do frontend
- Demais bibliotecas auxiliares

Observação: o artigo cita HTML + Tailwind + JavaScript para a interface; a definição vigente do autor é **TypeScript + Tailwind**, que prevalece.

Se uma tarefa exigir uma decisão pendente, **pare, apresente as opções com prós e contras e peça aprovação** (ver seção 6).

---

## 4. Princípios de conduta

1. **Entenda antes de implementar.** Releia os requisitos e as especificações relevantes. Se não conseguir apontar qual requisito justifica a mudança, não implemente.
2. **Nada sem justificativa.** Não crie funcionalidades, endpoints, campos, telas ou configurações que não estejam ligados a um requisito ou a uma especificação aprovada.
3. **Não invente.** Não invente protocolos de balança, comandos de cancela, formatos de quadro serial, esquemas de banco, contratos de API, versões de bibliotecas nem regras de negócio. Se não está no artigo, neste repositório ou numa decisão aprovada, é uma **pergunta**, não uma suposição.
4. **Separe fatos de hipóteses.** Ao escrever documentação, specs ou respostas, rotule o que é [ARTIGO], [DEFINIDO], [PROPOSTA] ou [PENDENTE].
5. **Peça esclarecimento** quando houver ambiguidade relevante (comportamento operacional, segurança, dados, escopo). Faça perguntas objetivas, agrupadas, com a opção que você recomenda e por quê.
6. **Preserve a arquitetura e as tecnologias aprovadas.** Mudanças estruturais passam por ADR (seção 9) e aprovação.
7. **Mudanças pequenas e rastreáveis.** Prefira incrementos curtos, cada um ligado a um requisito/tarefa.
8. **Honestidade sobre verificação.** Nunca afirme que testou, executou, compilou, rodou um comando ou validou algo se isso não aconteceu **nesta sessão**, com saída observada. Diga explicitamente: "não executado", "não verificado" ou "verificado apenas por leitura". Se um comando falhou, reporte a falha; não a esconda nem a descreva como sucesso.
9. **Sem hardware real, sem afirmação sobre hardware real.** Comportamento com balança, cancelas e câmeras reais só pode ser dado como validado se houver teste real registrado. Simulações validam a lógica do sistema, não o equipamento.

---

## 5. Fluxo de trabalho SDD (Spec-Driven Development)

Toda mudança não trivial segue as fases abaixo. Nenhuma fase é pulada; as portas de aprovação (**🔒**) exigem confirmação explícita do autor antes de avançar.

| # | Fase | O que fazer | Saída | Porta |
|---|---|---|---|---|
| 1 | **Requisitos** | Identificar/registrar requisitos (RF, RNF, RN) a partir do artigo e de conversas com o autor. Marcar ambiguidades. | `specs/requisitos.md` atualizado | 🔒 se houver requisito novo ou alterado |
| 2 | **Especificação** | Detalhar a feature: comportamento, regras, estados, falhas, critérios de aceitação verificáveis. Sem código. | `specs/features/NNN-slug/spec.md` | 🔒 status → *Aprovada* |
| 3 | **Análise de impacto** | Listar módulos, dados, segurança operacional, testes, documentação e specs afetados; riscos; reversibilidade. | seção "Impacto" da spec | — |
| 4 | **Planejamento** | Quebrar em tarefas pequenas e ordenadas, cada uma ligada a critérios de aceitação; definir estratégia de teste. | `specs/features/NNN-slug/plano.md` | 🔒 se envolver decisão pendente |
| 5 | **Implementação** | Implementar **somente** o que a spec aprovada cobre, tarefa por tarefa. | código + testes | — |
| 6 | **Testes** | Criar e executar testes para cada critério de aceitação (seção 8). | testes + relatório de execução | — |
| 7 | **Revisão** | Autorrevisão contra a spec e as regras deste arquivo; atualizar specs/docs/ADRs; relatar honestamente. | relatório final (seção 11) | 🔒 aceite do autor |

Regras do fluxo:

- **A spec é a fonte de verdade.** Se o código precisar divergir dela, **atualize a spec primeiro** (com aprovação) e só então o código. Nunca deixe código e spec discordando.
- Se durante a implementação surgir algo que a spec não cobre, **pare e pergunte**; não improvise.
- Correção de bug também passa pelo fluxo, de forma reduzida: reproduzir → ligar ao requisito/critério violado → corrigir → teste de regressão.
- Mudanças triviais (typo, comentário, formatação sem efeito funcional) podem dispensar spec, mas continuam sendo reportadas.

### 5.1 Organização das especificações

Abordagem simples, só com Markdown versionado no repositório, sem depender de plugins ou ferramentas específicas do OpenCode. O agente deve **ler os arquivos explicitamente** (não assuma carregamento automático além do próprio `AGENTS.md`).

```
specs/
├── README.md                  # índice e status de cada spec
├── requisitos.md              # RF-xxx, RNF-xxx, RN-xxx (com origem: artigo / autor)
├── glossario.md               # termos: tara, peso bruto, peso líquido, ROI, etc.
└── features/
    └── NNN-slug/              # ex.: 001-...  (numeração sequencial)
        ├── spec.md            # o quê e por quê (comportamento, regras, critérios)
        ├── plano.md           # como (tarefas, ordem, testes)
        └── tarefas.md         # (opcional) checklist de acompanhamento
docs/
└── decisoes/
    └── ADR-NNNN-titulo.md     # decisões arquiteturais (seção 9)
```

Convenções:

- **IDs estáveis**: `RF-001` (funcional), `RNF-001` (não funcional), `RN-001` (regra de negócio), `CA-001` (critério de aceitação, escopado à feature). Nunca reutilize um ID; marque como *Obsoleto*.
- **Status da spec**: `Rascunho` → `Em revisão` → `Aprovada` → `Implementada` → `Obsoleta`.
- **Rastreabilidade**: cada teste cita o(s) `CA-`/`RF-` que verifica; cada spec cita a origem do requisito ([ARTIGO] ou decisão do autor).
- Conteúdo mínimo de uma `spec.md`: contexto e origem; objetivo; fora de escopo; atores; pré-condições; comportamento normal; **comportamento em falha** (obrigatório); regras de negócio; estados e transições afetados; dados envolvidos (sem esquema prematuro); critérios de aceitação verificáveis; impacto; perguntas em aberto.
- Esta estrutura é uma proposta. Antes de criá-la, o agente deve confirmar com o autor.
- **Situação:** estrutura confirmada pelo autor (C-003, 2026-10-29) e já em uso.

### 5.2 Ordem sugerida das primeiras especificações

Os itens 1 a 5 já foram feitos (requisitos, ADR-0001 e specs 004 a 006). O item 6 depende dos contratos e das telas (`specs/tarefas-iniciais.md`).

1. Requisitos consolidados (a partir do artigo e do autor).
2. ADR de banco de dados (ADR-0001, Aceita).
3. Fluxo operacional e máquina de estados da operação (incluindo estados de falha e intervenção manual).
4. Camada de dispositivos (balança/cancela) com interface abstrata e simuladores — sem depender de protocolo real ainda.
5. Pipeline de LPR (aquisição → ROI → OCR → validação) com fonte de imagens substituível.
6. Interface de monitoramento e administração.

---

## 6. Ambiguidades e perguntas

- Se um requisito admite duas interpretações com comportamento operacional diferente, **pergunte**. Não escolha por conveniência.
- Formato recomendado da pergunta: contexto (1–2 linhas) → opções → recomendação e motivo → impacto de cada opção.
- Registre perguntas não respondidas na seção "Perguntas em aberto" da spec ou em `AMBIENTE.md`, e **não implemente a parte afetada** até haver resposta.
- Enquanto houver pendência, é aceitável implementar apenas o que **não depende** dela, se isolado e reversível.

---

## 7. Segurança operacional (prioridade máxima)

O sistema aciona cancelas e lê uma balança industrial. Falhas têm consequências físicas e de integridade de dados. Estas regras prevalecem sobre conveniência, desempenho ou elegância do código.

### 7.1 Princípios

1. **Falha segura (fail-safe).** Em qualquer dúvida, o sistema **não autoriza** e **não aciona**: mantém o estado seguro e encaminha para intervenção do operador/administrador.
2. **Nunca autorizar por inferência.** Entrada só é autorizada com: placa reconhecida com confiança suficiente **e** validada **e** agendamento correspondente válido **e** estado operacional compatível.
3. **Ação física exige estado conhecido.** Comandos às cancelas só são emitidos se o estado atual da operação os permitir. Comando sem confirmação de resultado é tratado como **estado desconhecido**, não como sucesso.
4. **Não reenviar comandos físicos cegamente.** Retentativas de comando a cancela só com política definida em spec (limites, intervalo, idempotência) — e nunca em loop ilimitado.
5. **Ordem e transições explícitas.** Toda operação percorre uma máquina de estados **explícita**; transições inválidas são **rejeitadas e registradas**, nunca "corrigidas" silenciosamente.
6. **Rastreabilidade.** Eventos relevantes (reconhecimento, decisão de autorização, comandos, leituras de peso aceitas, falhas, intervenções manuais) devem ser registráveis para auditoria. O conteúdo exato é definido em spec.
7. **O software não é a única barreira de segurança física.** Nunca presuma que o código substitui intertravamentos, sensores de presença ou parada de emergência. Se a spec depender disso, registre como premissa a confirmar com o autor.

### 7.2 Situações que o código **deve** tratar explicitamente

| Situação | Comportamento esperado (princípio; detalhes em spec) |
|---|---|
| Falha/timeout de comunicação serial com a balança | Não registrar peso; sinalizar falha; manter estado seguro; permitir ação do operador. |
| Leitura de peso instável, ausente, malformada ou fora de faixa | Não aceitar; nunca "arredondar" ou preencher valor; registrar a ocorrência. |
| Falha/ausência de resposta da cancela | Tratar estado como desconhecido; não assumir aberta nem fechada; alertar. |
| Reconhecimento de placa inconclusivo ou baixa confiança | Não autorizar; mostrar evidência (imagem/ROI/leitura) ao operador; permitir decisão manual conforme regra aprovada. |
| Placa lida sem agendamento correspondente | Não autorizar; registrar o evento. |
| Mais de um agendamento/veículo candidato (ambiguidade) | Não escolher automaticamente; escalar. |
| Câmera indisponível ou frame inválido | Não decidir com dados ausentes; sinalizar. |
| Estado operacional inválido ou transição inesperada | Rejeitar, registrar, manter estado seguro. |
| Queda/reinício do backend no meio de uma operação | Retomar a partir de estado persistido de forma segura, sem repetir comandos físicos sem verificação (comportamento a especificar). |
| Concorrência (dois eventos para o mesmo veículo/operação) | Garantir atomicidade e consistência; sem pesagens duplicadas. |

### 7.3 Regras de código para dispositivos

- Acesso à balança e às cancelas **somente** por uma camada de dispositivos com interface abstrata; implementações real (PySerial) e simulada trocáveis por configuração.
- Toda leitura/escrita serial com **timeout** definido; nunca bloquear indefinidamente.
- Entradas vindas de equipamento, câmera e OCR são **não confiáveis**: validar formato, faixa e coerência antes de usar.
- Nenhuma lógica de negócio de segurança deve viver apenas no frontend.
- Em modo de desenvolvimento/teste, o sistema **nunca** deve acionar hardware real por acidente: o modo simulado deve ser o padrão seguro, e o uso de hardware real deve exigir configuração explícita.
- Não logar nem expor dados pessoais ou imagens além do necessário (placas e dados de motorista podem ser dados pessoais; retenção das imagens: RN-022; adequação à LGPD **[PENDENTE]**, Q-08).

---

## 8. Testes

- **Cada funcionalidade nasce com testes** ligados aos critérios de aceitação da spec. Sem teste, a tarefa não está concluída.
- Cobrir sempre: caminho normal, **caminhos de falha** (seção 7.2) e casos-limite.
- Pirâmide sugerida **[PROPOSTA]**: testes unitários (regras de negócio, normalização/validação de placa, cálculo de peso líquido, máquina de estados) → integração (API + banco, camada de dispositivos simulada) → ponta a ponta com simuladores.
- **Dispositivos**: use simuladores de balança e cancela com cenários configuráveis (leitura estável, instável, timeout, quadro corrompido, resposta ausente). Não dependa de hardware real nos testes automatizados.
- **Visão computacional**: use um conjunto de imagens/vídeos de referência com resultado esperado (ground truth) e fonte de imagens substituível. Testes de LPR devem ser reproduzíveis sem câmera conectada. Não "ajuste" o conjunto de teste para fazer o teste passar.
- Testes de persistência devem rodar contra o **mesmo motor de banco** que será usado na execução, quando a decisão estiver tomada (PostgreSQL, ADR-0001).
- Execute os testes relevantes **antes** de declarar a tarefa concluída e relate o resultado real (comando, resultado, falhas). Se não foi possível executar, diga isso.
- Ferramentas de teste do backend: pytest (ADR-0003). As do frontend são **[PENDENTE]** até serem aprovadas; não presuma uma.

---

## 9. Documentação e decisões arquiteturais

- Toda decisão arquitetural relevante (banco, framework do frontend, ORM, autenticação, modelo de processos para OCR/serial, formato de streaming de vídeo, etc.) gera um **ADR** em `docs/decisoes/ADR-NNNN-titulo.md` com: contexto, opções consideradas, decisão, consequências, status (`Proposta` / `Aceita` / `Substituída`).
- ADRs começam como **Proposta**; só viram **Aceita** com aprovação do autor.
- Mantenha atualizados, na mesma mudança que os afeta: spec(s), `AMBIENTE.md`, este arquivo (se as regras mudarem) e o README (quando existir).
- Documente **o porquê**, não só o quê. Comentários de código explicam intenção e restrições (especialmente de segurança), não o óbvio.
- Se uma informação do `AMBIENTE.md` deixar de ser verdadeira, atualize-o ou sinalize ao autor.
- Projeto open-source **[ARTIGO]**: documentação básica de instalação, configuração e execução e definição de licença são desejáveis; a licença é **[PENDENTE]**. Não escolha uma licença por conta própria.

---

## 10. Qualidade de código

- **Tipado**: Python com anotações de tipo em código novo; TypeScript em modo estrito **[PROPOSTA]**. Evite `Any`/`any` sem justificativa.
- **Organizado e coeso**: módulos com responsabilidade única; regras de negócio **separadas** de I/O (HTTP, serial, câmera, banco) para serem testáveis isoladamente.
- **Testável**: injete dependências (dispositivos, câmera, relógio, repositórios) em vez de acessá-las globalmente.
- **Legível**: nomes claros e consistentes. Idioma: termos do domínio em português **[PROPOSTA]** (ex.: placa, agendamento, pesagem); identificadores técnicos em inglês são aceitáveis — **peça ao autor para fixar a convenção** e siga-a de forma uniforme. A convenção já foi fixada no `CONVENCOES.md` (D-10).
- **Erros explícitos**: sem `except` genérico que engula falhas; erros de dispositivo e de reconhecimento são tipos/estados tratados, não exceções ignoradas.
- **Validação nas fronteiras**: entradas da API, da serial, da câmera e do OCR.
- **Configuração por ambiente**: nada de portas seriais, URLs, credenciais ou limiares fixos no código; segredos nunca no repositório.
- **Operações bloqueantes** (OCR, leitura serial, captura de vídeo) não devem bloquear o ciclo de atendimento de requisições da API; a estratégia concreta está decidida em parte; o restante é **[PENDENTE]** (D-05, `AMBIENTE.md` §15).
- Ferramentas de formatação/lint/tipagem estática do backend: ADR-0003. As do frontend: **[PENDENTE]**; proponha, não imponha.

### 10.1 Dependências e abstrações

- **Evite dependências desnecessárias.** Antes de adicionar uma, justifique: o problema que resolve, por que a biblioteca padrão/stack definida não basta, manutenção e licença (compatível com projeto open-source). Peça aprovação.
- **Não invente versões.** Só fixe uma versão de biblioteca/ferramenta com justificativa (ex.: compatibilidade verificada) e registre o motivo.
- **Sem abstração prematura.** Crie interfaces/camadas apenas quando houver necessidade concreta. Exceções já justificadas pelo artigo e pela segurança: separação por módulos (interface web, API, LPR, comunicação serial, banco) **[ARTIGO]** e abstração dos dispositivos com versão simulada **[ARTIGO]** (simulação prevista para validação).
- Não crie código "para o futuro" (flags, ganchos, campos, endpoints) sem requisito.

---

## 11. Relato de trabalho (ao final de cada tarefa)

Responda de forma curta e honesta, contendo:

1. **O que foi feito** e a quais requisitos/spec/tarefa se liga.
2. **Arquivos alterados/criados.**
3. **Verificação**: testes/comandos **realmente executados** e o resultado; o que **não** foi executado ou verificado, e por quê.
4. **Decisões tomadas** (e ADRs criados/atualizados) e **suposições** feitas, marcadas como tal.
5. **Pendências e perguntas** que bloqueiam ou afetam o próximo passo.
6. **Riscos** de segurança operacional percebidos.

---

## 12. Proibições (resumo)

- Substituir tecnologias **[DEFINIDO]**.
- Escolher sozinho itens **[PENDENTE]** ou transformar **[PROPOSTA]** em decisão.
- Implementar o que não tem requisito/spec aprovada.
- Criar esquema de banco, migrations, endpoints ou contratos antes da spec funcional correspondente estar aprovada.
- Automatizar o **agendamento** (fora do escopo; é sempre uma ação humana, de usuário com permissão ou do motorista no autoatendimento; RN-001, ADR-0004).
- Autorizar entrada, acionar cancela ou registrar peso em situação inconclusiva ou inválida.
- Acionar hardware real sem configuração explícita.
- Afirmar que algo foi testado/executado/validado sem ter sido.
- Adicionar dependências sem justificativa e aprovação.
- Inventar protocolos, formatos de quadro, comandos de equipamento, versões ou números.
- Fazer commit/push, apagar dados ou reescrever histórico sem pedido explícito do autor.

---

## 13. Definição de pronto

Uma tarefa só está **pronta** quando:

- [ ] Está ligada a requisito(s) e a uma spec **Aprovada**.
- [ ] Os critérios de aceitação têm testes, e os testes relevantes foram **executados** com resultado relatado.
- [ ] Os caminhos de falha da seção 7.2 aplicáveis foram tratados e testados.
- [ ] Spec, `AMBIENTE.md` e ADRs afetados estão atualizados.
- [ ] Não há dependência ou abstração sem justificativa.
- [ ] O relato final (seção 11) foi entregue com honestidade sobre o que não foi verificado.
- [ ] O autor aceitou o resultado.
