---
version: 1
slug: "src-componentes-layoutbase-tsx"
primary_target: "src/componentes/LayoutBase.tsx"
related_targets: ["src/paginas/totem/PaginaAutoatendimento.tsx"]
---

# Casca das telas internas e do totem (FE-102)

Mode: Operate. Público: operador, administrador e auditor na sala da balança (monitor a 60 cm, luz comum); motorista no totem de toque. Tarefa: saber de relance o estado da balança, o modo dos equipamentos e se a tela está atualizada; agir só pelas ações que o backend oferece. Sem telas de negócio nesta tarefa.

Aberto: tamanho de tela do totem; tipo de câmera (Q-06).

## Direction contract

THESIS: A tela é a sinalização de segurança do pátio. Cada estado tem palavra, forma e cor fixas, como uma placa NR-26. Recusa o painel cinza com um acento e cartões com sombra, onde falha e sucesso parecem iguais.

OWN-WORLD: Chão de concreto claro, tinta quase preta, cabeçalho asfalto com a faixa amarela de demarcação embaixo. Vermelho falha/parar (círculo), amarelo atenção (triângulo), verde ok (quadrado cheio), azul só para "ação disponível agora". Fios de 1px, sem sombra, sem raio grande. Fonte do sistema; caixa alta curta nos rótulos de estado; números tabulares; placa sempre na mesma fonte monoespaçada.

STORY: O operador vê o modo, a frescura e o que pede ação antes de ler qualquer tabela. Sabe que um clique só pede; o resultado físico vem depois.

FIRST VIEWPORT: Cabeçalho asfalto com EasyScale à esquerda, navegação no centro, usuário à direita; à direita do nome, a placa de modo (REAL em campo vermelho cheio com triângulo, a mais forte; SIMULADO contornada em azul; desconhecido em campo amarelo). Faixa amarela. Área de trabalho em concreto. Quando a tela está desatualizada, uma faixa zebrada preto-amarelo fica sobre a barra de ações, com triângulo e o texto do bloqueio; os botões continuam à vista, desabilitados.

FORM: Sinalização de segurança industrial (NR-26/ISO 7010), candidato 5 da lista; seed e0146144. Raises: fios de 1px (do anuário de pranchas); placa como chave cruzada em toda tela (do catálogo de evento); estado nunca só por cor (do trilho central); azul reservado à ação disponível (do mapa de orientação).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
