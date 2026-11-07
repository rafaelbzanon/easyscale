---
name: EasyScale
description: Telas da pesagem rodoviária com LPR, desenhadas como a sinalização de segurança do pátio.
colors:
  concreto: "#eeedea"
  painel: "#e3e2de"
  fio: "#9c9a94"
  tinta: "#1b1d20"
  suave: "#4a4d52"
  asfalto: "#23262a"
  claro: "#f2f1ee"
  amarelo: "#f2c200"
  vermelho: "#b3261e"
  verde: "#1e6b3a"
  azul: "#1d4f91"
typography:
  headline-totem:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 700
    lineHeight: 1.111
  marca-totem:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "1.875rem"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.333
  body-totem:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1.4
    fontFeature: "tnum"
  marca:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.556
    letterSpacing: "-0.025em"
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  label:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.429
    fontFeature: "tnum"
  label-estado:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.429
    letterSpacing: "0.025em"
rounded:
  nenhum: "0px"
spacing:
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
components:
  botao-acao:
    backgroundColor: "{colors.azul}"
    textColor: "{colors.claro}"
    typography: "{typography.label}"
    rounded: "{rounded.nenhum}"
    padding: "0 16px"
    height: "40px"
  botao-acao-hover:
    backgroundColor: "{colors.tinta}"
    textColor: "{colors.claro}"
  botao-neutro:
    backgroundColor: "transparent"
    textColor: "{colors.tinta}"
    typography: "{typography.label}"
    rounded: "{rounded.nenhum}"
    padding: "0 16px"
    height: "40px"
  botao-desabilitado:
    backgroundColor: "{colors.painel}"
    textColor: "{colors.suave}"
  botao-totem:
    typography: "{typography.body-totem}"
    rounded: "{rounded.nenhum}"
    padding: "0 24px"
    height: "64px"
  placa-modo-real:
    backgroundColor: "{colors.vermelho}"
    textColor: "{colors.claro}"
    typography: "{typography.label-estado}"
    rounded: "{rounded.nenhum}"
    padding: "4px 12px"
  placa-modo-simulado:
    backgroundColor: "{colors.claro}"
    textColor: "{colors.tinta}"
    typography: "{typography.label-estado}"
    rounded: "{rounded.nenhum}"
    padding: "4px 12px"
  placa-modo-desconhecido:
    backgroundColor: "{colors.amarelo}"
    textColor: "{colors.tinta}"
    typography: "{typography.label-estado}"
    rounded: "{rounded.nenhum}"
    padding: "4px 12px"
  aviso-bloqueio:
    backgroundColor: "{colors.amarelo}"
    textColor: "{colors.tinta}"
    typography: "{typography.label-estado}"
    rounded: "{rounded.nenhum}"
    padding: "4px 12px"
  mensagem-erro:
    backgroundColor: "{colors.claro}"
    textColor: "{colors.vermelho}"
    rounded: "{rounded.nenhum}"
    padding: "12px"
  cabecalho:
    backgroundColor: "{colors.asfalto}"
    textColor: "{colors.claro}"
    padding: "12px 16px"
---

# Design System: EasyScale

## Overview

**Creative North Star: "A Sinalização do Pátio"**

A tela é a sinalização de segurança do pátio da balança. Cada estado tem palavra, forma e cor fixas, como uma placa NR-26 ou ISO 7010. O operador lê o modo, a frescura dos dados e o que pede ação antes de ler qualquer tabela.

O chão é concreto claro. A tinta é quase preta. O cabeçalho é asfalto, com a faixa amarela de demarcação embaixo. A superfície é plana: fios de 1px separam as áreas, sem sombra e sem canto arredondado. A densidade serve a quem opera o dia todo. O totem usa a mesma linguagem, maior e mais simples.

O sistema recusa o painel cinza com um acento só e os cartões com sombra, onde falha e sucesso parecem iguais.

**Key Characteristics:**

- Cor só com função. Nenhuma cor decorativa.
- Estado sempre em palavra e forma juntas, nunca só por cor.
- Cabeçalho asfalto com faixa amarela de 4px.
- Fios de 1px, sem sombra, cantos retos.
- Fonte do sistema com números tabulares.
- Faixa zebrada só no bloqueio de ações.

## Colors

Paleta de sinalização industrial: neutros de concreto e asfalto, e quatro cores de segurança, cada uma com uma função só.

### Primary

- **Azul Ação** (azul): ação disponível agora. Fundo do botão de ação, link e anel de foco. Também marca o modo SIMULADO, na borda da placa e no círculo cheio.

### Secondary

- **Vermelho Parar** (vermelho): falha e modo REAL. Campo cheio da placa REAL, borda e texto da mensagem de erro, círculo cortado de falha.
- **Amarelo Demarcação** (amarelo): atenção, desconhecido e bloqueio. Faixa do cabeçalho, triângulo de atenção, placa de modo desconhecido, aviso de bloqueio, seleção de texto e anel de foco dentro do cabeçalho.

### Tertiary

- **Verde Liberado** (verde): ok. Só no quadrado cheio do símbolo de estado. Ainda não aparece em tela pronta.

### Neutral

- **Concreto** (concreto): fundo da página.
- **Painel** (painel): fundo do botão desabilitado.
- **Fio** (fio): fios de 1px e borda do botão desabilitado.
- **Tinta** (tinta): texto principal, contorno do triângulo, listra escura da faixa zebrada.
- **Tinta Suave** (suave): texto secundário e texto do botão desabilitado.
- **Asfalto** (asfalto): fundo do cabeçalho.
- **Claro** (claro): texto sobre asfalto, vermelho e azul; fundo da placa SIMULADO e da mensagem de erro. No cabeçalho, o texto secundário usa claro a 80%.

### Named Rules

**The Cor Com Função Rule.** Toda cor fora dos neutros diz um estado. Se a cor não responde "o que isto significa?", ela não entra.

**The Azul Reservado Rule.** Azul é ação disponível agora, e o modo SIMULADO. Não use azul para destaque, título ou enfeite.

**The REAL Mais Forte Rule.** REAL é a placa de maior peso na tela: campo vermelho cheio com triângulo. SIMULADO é só contorno azul. Desconhecido é campo amarelo. Na dúvida, a tela mostra desconhecido, nunca SIMULADO.

## Typography

**Display Font:** nenhuma. Não há face de display definida.
**Body Font:** pilha do sistema (system-ui, -apple-system, Segoe UI, Roboto, Noto Sans, Liberation Sans, sans-serif)
**Label/Mono Font:** pilha monoespaçada do sistema declarada como token (ui-monospace, SF Mono, Cascadia Mono, DejaVu Sans Mono, Liberation Mono, monospace). Ainda sem uso.

**Character:** letra de painel de instrumento. Neutra, legível a 60 cm, com números tabulares em toda a página para valores que não dançam.

### Hierarchy

- **Headline do totem** (700, 2.25rem, 1.111): título da tela do motorista.
- **Marca do totem** (700, 1.875rem, 1.2, -0.025em): nome EasyScale no cabeçalho grande.
- **Headline** (700, 1.5rem, 1.333): título da página interna, largura de até 65ch.
- **Body do totem** (400, 1.25rem, 1.4): todo texto e botão do totem.
- **Marca** (700, 1.125rem, 1.556, -0.025em): nome EasyScale no cabeçalho interno. O título de contexto vem ao lado, em peso normal.
- **Body** (400, 1rem, 1.5): texto corrido.
- **Label** (600, 0.875rem, 1.429): botões e dados do usuário no cabeçalho.
- **Label de estado** (700, 0.875rem, 0.025em, caixa alta curta): palavra de estado na placa, como REAL, SIMULADO e MODO DESCONHECIDO.

### Named Rules

**The Número Tabular Rule.** `tabular-nums` vale na raiz. Peso, hora e contagem alinham em coluna.

**The Caixa Alta É Estado Rule.** Caixa alta só na palavra de estado dentro de uma placa. Nunca em rótulo de seção ou sobre título.

## Layout

Coluna única por página. As telas internas centralizam o conteúdo em até 1536px, com 16px de margem lateral e 24px de respiro vertical. Páginas de texto limitam a linha a 65ch. O totem centraliza uma coluna de até 48rem na vertical, com 24px entre blocos e 32px de respiro.

O cabeçalho é uma linha que quebra: marca à esquerda, placa de modo ao lado, usuário e Sair empurrados à direita. Em tela estreita, os itens descem para a linha de baixo com 8px entre linhas e 24px entre itens. Não há breakpoints próprios.

Ritmo de espaço em passos de 4px: 8px entre itens próximos, 12px dentro de placas e caixas, 16px de margem, 24px entre blocos, 32px no totem.

## Elevation & Depth

Sistema plano. Não há sombra. A profundidade vem do tom (asfalto sobre concreto), da faixa amarela de 4px e de fios de 1px. O foco usa contorno de 3px com 2px de afastamento, azul na página e amarelo no cabeçalho.

### Named Rules

**The Sem Sombra Rule.** Nenhuma superfície flutua. Separação é fio, tom ou faixa.

## Shapes

Cantos retos em tudo (0px). Bordas de 1px nos botões, na mensagem de erro e na linha da área de ações. A placa de modo usa borda de 2px para pesar mais. As formas de estado seguem a ISO 7010: triângulo para atenção, círculo cortado para falha, quadrado cheio para ok, círculo cheio para informação e ação. O símbolo tem a altura da letra ao lado (1em).

A faixa zebrada é a única textura: listras a -45°, amarelo e tinta, 14px cada.

### Named Rules

**The Palavra E Forma Rule.** Todo estado leva a palavra e a forma ISO 7010 juntas. A cor reforça, nunca carrega sozinha.

**The Zebrada É Bloqueio Rule.** A faixa zebrada aparece só sobre a área de ações bloqueada por tela desatualizada. Em nenhum outro lugar.

## Components

### Buttons

Retos e firmes, como botoeira de painel.

- **Shape:** cantos retos (0px), borda de 1px, altura mínima de 40px.
- **Ação:** fundo azul, texto claro, 16px de margem lateral. Só para a ação disponível agora.
- **Neutro:** fundo transparente, texto e borda na cor do contexto. Serve no concreto e no asfalto.
- **Hover / Focus:** a ação escurece para tinta; o neutro ganha 15% da cor do texto no fundo. Transição de cor em 150ms. Foco no contorno de 3px descrito em Elevation & Depth.
- **Desabilitado:** fundo painel, texto suave, borda fio, cursor de proibido. Continua visível.
- **Totem:** dentro do totem, todo botão tem altura mínima de 64px, 24px de margem lateral e texto de 1.25rem.

### Cabeçalho

- **Style:** fundo asfalto, texto claro, faixa amarela de 4px na borda de baixo. 12px de respiro vertical nas telas internas e 20px no totem.
- **Conteúdo:** marca EasyScale, placa de modo, nome e perfil do usuário, botão Sair neutro.

### Placa de Modo (signature)

A chave de leitura de toda tela interna. Borda de 2px, cantos retos, símbolo, palavra em caixa alta e um complemento curto.

- **REAL:** campo vermelho cheio, texto claro, triângulo. Lista os equipamentos físicos.
- **SIMULADO:** fundo claro, borda azul, círculo azul cheio.
- **Desconhecido:** campo amarelo, borda tinta, triângulo. Qualquer dado ausente ou inesperado cai aqui.

### Área de Ações (signature)

- **Style:** fio de 1px no topo, botões em linha com 8px entre eles.
- **Bloqueada:** faixa zebrada por cima, com um aviso amarelo central em negrito, triângulo e o texto do bloqueio. Os botões ficam à vista e desabilitados.

### Mensagem de Erro

- **Style:** fundo claro, borda vermelha de 1px, 12px de respiro. Círculo cortado, texto vermelho em 600 e, quando cabe, o botão neutro Tentar de novo.

## Do's and Don'ts

### Do:

- **Do** dar a todo estado palavra e forma ISO 7010 juntas.
- **Do** usar azul só na ação disponível agora e no modo SIMULADO.
- **Do** mostrar a placa de modo em toda tela interna, com REAL no campo vermelho cheio.
- **Do** separar áreas com fio de 1px na cor fio.
- **Do** manter botões bloqueados visíveis e desabilitados, sob a faixa zebrada.
- **Do** dar 64px de altura mínima a todo alvo de toque do totem.

### Don't:

- **Don't** usar sombra em nenhuma superfície.
- **Don't** arredondar cantos.
- **Don't** indicar estado só por cor.
- **Don't** usar cor sem função, nem azul como destaque.
- **Don't** usar a faixa zebrada fora do bloqueio de ações.
- **Don't** pôr caixa alta em rótulo de seção ou sobre título.
