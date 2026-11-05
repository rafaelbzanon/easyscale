# ADR-0002 — Monólito modular vs. serviços separados

- **Trilha:** Comum
- **Status:** Aceita
- **Data:** 2026-10-29
- **Decisão relacionada:** D-07 — `AMBIENTE.md` §4.3, §15
- **Tarefa:** C-202 (`specs/tarefas-iniciais.md`)
- **Riscos relacionados:** R-04 (OCR em CPU bloqueando a API), R-05 (portas seriais em contêiner)
- **Aprovação:** autor, 2026-10-29 ("pode prosseguir" em resposta à porta 🔒 da C-202)

---

## 1. Contexto

- O artigo prevê organização **em módulos** — interface web, API backend, reconhecimento de placas, comunicação serial RS232 e banco relacional — para facilitar desenvolvimento, manutenção e validação individual **[ARTIGO §2, §4]** (RNF-001). Fala em módulos, não em serviços.
- O escopo é um **protótipo** validado em ambiente controlado, com um ponto de pesagem previsto (Q-12 em aberto) **[ARTIGO §1]**.
- Restrições já registradas:
  - **Um único dono por porta serial** (`AMBIENTE.md` §4.2 item 3): só um processo pode abrir cada porta.
  - OCR, leitura serial e captura de imagem não podem bloquear a API (RNF-011); a estratégia concreta é D-05, decidida na spec `orquestracao-operacao` (BE-601).
  - Acesso a portas seriais dentro de contêiner é direto em Linux e limitado em Docker Desktop (Windows/macOS) (R-05, Q-07).
- A árvore de pastas aprovada (`CONVENCOES.md` §2) já organiza o backend como **um pacote** `pesagem` com módulos `api`, `dominio`, `orquestracao`, `lpr`, `dispositivos`, `persistencia`, com regras de dependência P-4 a P-6.

## 2. Critérios

1. Atende à modularidade exigida pelo artigo.
2. Simplicidade para um protótipo de TCC (menos peças para configurar, depurar e documentar).
3. Garante um único dono por porta serial.
4. Permite isolar operações bloqueantes (D-05) sem reescrita.
5. Reprodutibilidade em Docker e viabilidade com hardware real (R-05).

## 3. Opções consideradas

| Opção | Descrição | Prós | Contras |
|---|---|---|---|
| **A. Monólito modular** | Um código-fonte (`backend/src/pesagem/`), um serviço `backend`; módulos separados por pacote e regras de dependência. | Mais simples de rodar, testar e documentar; modularidade garantida pelas regras P-4 a P-6; um só lugar para abrir as portas seriais; casa com a árvore aprovada. | Se mal isolado, OCR pode competir com a API por CPU (tratado por D-05); escalar partes separadamente não é possível (não é requisito). |
| **B. Monólito modular com processo de trabalho separado** | Mesmo código-fonte, mas dois processos/serviços: API e um *worker* que executa LPR e dispositivos. | Isola carga do OCR e a posse das portas seriais; continua um único código. | Exige comunicação entre processos (fila, banco ou outro) — decisão extra; mais configuração. |
| **C. Serviços separados** | Serviços independentes (ex.: LPR, dispositivos, API), cada um com seu código e contrato. | Isolamento máximo; troca independente de partes. | Contratos internos, rede, versionamento e falhas parciais adicionais; desproporcional para o protótipo; o artigo não pede. |

## 4. Decisão

**Opção A — monólito modular**, com as regras abaixo:

1. Um código-fonte e um serviço `backend`, conforme `CONVENCOES.md` §2.
2. Modularidade garantida pelas regras de dependência P-4 a P-6 (ex.: só `dispositivos/` importa `serial`; só `lpr/` importa `cv2`/`easyocr`; `dominio/` sem I/O).
3. **Posse das portas seriais**: as portas são abertas por **um único componente** da camada `dispositivos`, em **um único processo**. Consequência prática: o backend **não** pode ser executado com vários processos de servidor que abram as portas cada um (ex.: múltiplos *workers* do servidor ASGI) sem que a posse dos dispositivos seja isolada. A forma concreta é definida em D-05 (BE-601).
4. **Evolução para a opção B** fica permitida **sem novo ADR de arquitetura** se D-05 concluir que o OCR ou os dispositivos precisam de processo próprio, desde que: (a) continue um único código-fonte; (b) a posse das portas continue em um único processo; (c) a decisão seja registrada na spec/ADR de D-05.
5. Opção C fica descartada para o protótipo.

## 5. Consequências

- **Docker**: um `backend/Dockerfile` e um serviço `backend` no `compose.yaml` (BE-801, INT-001). Se D-05 levar à opção B, um segundo serviço pode usar a mesma imagem.
- **Portas seriais (R-05)**: no perfil `hardware-real`, o serviço que for dono dos dispositivos precisa do mapeamento da porta do host. Em Linux é direto; em Docker Desktop (Windows/macOS) pode não funcionar. Mitigação proposta: manter a possibilidade de executar o backend fora do contêiner nesse perfil. Depende de Q-07; **não verificado**.
- **Testes**: módulos testados isoladamente (unitários) e em conjunto com simuladores (integração), sem infraestrutura extra.
- **Desempenho**: a disputa de CPU entre OCR e API (R-04) precisa de medição real antes de D-05; nenhum número foi medido ainda.
- **Reversibilidade**: alta. Migrar de A para B é previsto na regra 4; migrar para C exigiria novo ADR e contratos internos.

## 6. Aprovação

- [x] Autor aprovou a opção A com as regras 1–5 em 2026-10-29.

Atualizados na mesma mudança: `AMBIENTE.md` §4.3 e §15 (D-07) e `specs/README.md`.
