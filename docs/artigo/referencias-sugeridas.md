# Referências sugeridas para o artigo do TCC

Levantamento feito em 2026-11-08 com a skill `deep-research` (modo `lit-review`) do plugin academic-research-skills, a partir de `docs/artigo/artigo-tcc.pdf`.

- **Tipo de revisão:** narrativa. As fontes foram escolhidas para reforçar trechos do artigo que hoje têm pouca ou nenhuma citação. Não é uma revisão sistemática e não cobre toda a literatura.
- **Verificação:** a existência e os dados bibliográficos de cada referência foram conferidos na web nesta data (editora, DOI, anais ou repositório). O conteúdo foi conferido apenas pelo resumo e por páginas de índice, **sem leitura do texto completo**, exceto a Portaria Inmetro nº 157/2022, cujo texto foi lido. Antes de citar, leia ao menos o trecho que sustenta a frase do artigo.
- **Formato:** as referências estão no estilo da lista atual do artigo (SBC). As frases sugeridas são rascunhos para você adaptar; nenhuma foi inserida no artigo.
- Referências que já estão no artigo não foram repetidas.

---

## 1. Por seção do artigo

### 2.1 Reconhecimento automático de placas

**[Lubna et al. 2021]** Revisão recente das etapas de ANPR (extração da placa, segmentação e reconhecimento dos caracteres), incluindo extração por bordas e reconhecimento por casamento de modelos. Complementa [Du et al. 2013] com uma revisão mais nova e de acesso aberto.
> Sugestão: "...dividem-se, em geral, em aquisição da imagem, localização da placa, segmentação e reconhecimento dos caracteres [Du et al. 2013, Lubna et al. 2021]."

**[Silva and Jung 2018]** Trabalho da UFRGS que detecta e retifica placas em vistas oblíquas antes do OCR. O artigo cita "ângulo" como fator de desempenho; esta referência mostra uma forma de tratá-lo e é de um grupo brasileiro.
> Sugestão, ao fim do 1º parágrafo: "...e há métodos que retificam placas vistas em ângulo antes do reconhecimento [Silva and Jung 2018]."

**[Laroca et al. 2022b]** (*A First Look at Dataset Bias...*). Um classificador simples identificou de qual base vinha uma imagem de placa com mais de 95% de acerto, em oito bases (quatro brasileiras, entre elas a RodoSol-ALPR). Os autores concluem que resultados medidos dentro de uma mesma base tendem a ser otimistas. Reforça diretamente o argumento do artigo de que o reconhecimento precisa ser avaliado com imagens do ambiente de uso.

**[Laroca et al. 2023]** (*Do We Train on Test Data?*). Imagens quase duplicadas entre treino e teste inflaram resultados de LPR. Ao refazer a divisão, as taxas caíram e a ordem dos modelos mudou em uma das bases.
> Sugestão, para as duas acima: "Além disso, vieses próprios de cada base [Laroca et al. 2022b] e imagens quase duplicadas entre treino e teste [Laroca et al. 2023] tendem a superestimar o desempenho medido, o que reforça a necessidade de avaliar o reconhecimento com imagens do ambiente de uso."

**[Gonçalves et al. 2016]** Base com 2.000 placas brasileiras (14.000 caracteres anotados) e protocolo de avaliação da segmentação. Serve como base pública brasileira citável nos trabalhos futuros (Seção 6), junto com a RodoSol-ALPR.

### 2.2 Processamento de imagens e OCR

**[Baek et al. 2019]** CRAFT, o detector de texto usado pelo EasyOCR. **[Shi et al. 2017]** CRNN, a arquitetura de reconhecimento em que se baseia o modelo de reconhecimento do EasyOCR.
> Sugestão: "O EasyOCR [...] combina um detector de regiões de texto [Baek et al. 2019] com um reconhecedor de sequências baseado em redes convolucionais e recorrentes [Shi et al. 2017]..."
> **Conferir antes:** a página oficial do EasyOCR [Jaided AI 2025] cita esses dois trabalhos como base. Confirme isso lá, porque eu não abri essa página.

**[Guo et al. 2017]** Redes neurais modernas são mal calibradas: a confiança que elas atribuem não corresponde à probabilidade real de acerto. Sustenta, com uma fonte de primeira linha, a frase do artigo de que o índice de confiança "não equivale, necessariamente, à probabilidade de a leitura estar correta".
> Sugestão: "...mas não equivale, necessariamente, à probabilidade de a leitura estar correta, pois redes neurais modernas tendem a ser mal calibradas [Guo et al. 2017]; por isso, o limiar..."

### 2.4 Pesagem rodoviária e agendamento

**[Inmetro 2022]** (Portaria nº 157/2022, RTM consolidado de instrumentos de pesagem não automáticos). **Texto lido.** No anexo, o item 3.4.6.3 proíbe a impressão "se o equilíbrio não for estável", e o item 3.4.7 proíbe armazenar indicações quando o equilíbrio não é estável. Hoje o artigo afirma que "o peso só deve ser registrado depois de estabilizado" sem citação; esta é a fonte normativa brasileira para isso.
> Sugestão: "...o peso só deve ser registrado depois de estabilizado; a regulamentação metrológica proíbe imprimir ou armazenar a indicação enquanto o equilíbrio não for estável [Inmetro 2022]."
> **Atenção:** o critério do item 3.4.6.4 (após 5 s, no máximo dois valores adjacentes indicados) é diferente do critério de demonstração do EasyScale (três leituras com variação de até 10 kg em 3 s). Não afirme conformidade com o RTM. O texto foi lido numa cópia não oficial (site da Sibapem); confira a vigência e o texto no site do Inmetro ou no DOU.

**[Giuliano and O'Brien 2007]** Estudo do sistema de agendamento dos portos de Los Angeles e Long Beach. Os autores **não encontraram evidência** de que o agendamento reduziu filas ou o tempo de atendimento. É uma evidência contrária útil: mostra que agendamento sozinho não garante ganho operacional, o que combina com a postura do artigo de não afirmar ganhos de tempo.
> Sugestão: "...terminais logísticos usam sistemas de agendamento [Gracia et al. 2025], embora seus efeitos sobre filas nem sempre se confirmem na prática [Giuliano and O'Brien 2007]..."

### 2.5 Sistemas web

**[Fielding 2000]** Tese que define o estilo REST. Hoje o artigo cita "API REST" sem referência.

**[Parnas 1972]** Trabalho clássico sobre critérios de divisão de um sistema em módulos. Fundamenta o monólito modular com fronteiras explícitas.
> Sugestão: "Um monólito modular [...] dividido em módulos com fronteiras explícitas [Parnas 1972]..."

**[Percival 2009]** Artigo que propõe o `scrypt` (função de derivação de chave com uso intenso de memória). O artigo usa `scrypt` na Seção 3.4 e hoje cita só a OWASP. Opcionalmente, cite também a especificação **[Percival and Josefsson 2016]** (RFC 7914).

### 3.1 Caracterização e processo de desenvolvimento

**[Hevner et al. 2004]** e **[Peffers et al. 2007]** Pesquisa em ciência do design: o conhecimento é produzido construindo e avaliando um artefato. Encaixa com "pesquisa aplicada, de natureza tecnológica, com desenvolvimento e avaliação de um protótipo" e dá respaldo metodológico a essa classificação.

**[Wazlawick 2014]** Referência brasileira de metodologia de pesquisa em computação, comum em TCCs. Alternativa ou complemento às duas acima.

**[Leveson and Turner 1993]** Análise dos acidentes do Therac-25: o equipamento passou a confiar no software para funções de segurança que, no modelo anterior, eram feitas por intertravamentos de hardware. Sustenta o princípio de falha segura e também a limitação de que o software não substitui barreiras físicas (sensores, intertravamentos).
> Sugestão, na Seção 3.1 ou nas limitações: "Adotou-se como princípio a falha segura [...]. O software, contudo, não substitui intertravamentos físicos, como mostram acidentes em que funções de segurança passaram a depender só do software [Leveson and Turner 1993]."

### 3.3 Modelagem (máquina de estados)

**[Harel 1987]** Statecharts, a base das máquinas de estados da UML. É uma referência formal para a máquina de estados explícita da Figura 3.

### 3.4 Decisões de implementação (simuladores)

**[Meszaros 2007]** Define o vocabulário de dublês de teste (*test doubles*: stubs, mocks etc.). Serve para nomear e justificar os simuladores que substituem balança, cancelas e câmera nos testes.

**[Björklund et al. 2019]** Redes treinadas só com placas sintéticas superaram sistemas treinados com imagens reais, desde que as imagens sintéticas variassem o suficiente. Use com cuidado: o trabalho trata de **treinar** com imagens sintéticas, e o EasyScale apenas **testa** com elas. Serve para contextualizar o uso de cenas sintéticas e, nos trabalhos futuros, como caminho para ampliar o acervo.

### 3.2 / Considerações finais (LGPD)

**[Brasil 2018]** Lei nº 13.709/2018 (LGPD). O artigo cita a lei no texto (Seção 3.2) mas ela **não está na lista de referências**. Pela ABNT e pela SBC, vale incluí-la.

---

## 2. Referências (formato SBC, prontas para colar)

[Baek et al. 2019] Baek, Y., Lee, B., Han, D., Yun, S., and Lee, H. (2019). Character region awareness for text detection. In *IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)*, pages 9365–9374.
*Conferir: o CVF lista as páginas 9365–9374 e um catálogo IEEE lista 9357–9366. DOI 10.1109/CVPR.2019.00959. Os coautores foram tirados da memória e não foram conferidos nesta busca.*

[Björklund et al. 2019] Björklund, T., Fiandrotti, A., Annarumma, M., Francini, G., and Magli, E. (2019). Robust license plate recognition using neural networks trained on synthetic images. *Pattern Recognition*, 93:134–146.

[Brasil 2018] Brasil (2018). Lei nº 13.709, de 14 de agosto de 2018: Lei Geral de Proteção de Dados Pessoais (LGPD). Diário Oficial da União, Seção 1, p. 59, 15 ago. 2018.

[Fielding 2000] Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures*. Tese (Doutorado em Information and Computer Science), University of California, Irvine.

[Giuliano and O'Brien 2007] Giuliano, G. and O'Brien, T. (2007). Reducing port-related truck emissions: The terminal gate appointment system at the Ports of Los Angeles and Long Beach. *Transportation Research Part D: Transport and Environment*, 12(7):460–473.

[Gonçalves et al. 2016] Gonçalves, G. R., Silva, S. P. G., Menotti, D., and Schwartz, W. R. (2016). Benchmark for license plate character segmentation. *Journal of Electronic Imaging*, 25(5):053034.

[Guo et al. 2017] Guo, C., Pleiss, G., Sun, Y., and Weinberger, K. Q. (2017). On calibration of modern neural networks. In *International Conference on Machine Learning (ICML)*, volume 70 of *PMLR*, pages 1321–1330.

[Harel 1987] Harel, D. (1987). Statecharts: A visual formalism for complex systems. *Science of Computer Programming*, 8(3):231–274.

[Hevner et al. 2004] Hevner, A. R., March, S. T., Park, J., and Ram, S. (2004). Design science in information systems research. *MIS Quarterly*, 28(1):75–105.

[Inmetro 2022] Inmetro (2022). Portaria nº 157, de 31 de março de 2022: Aprova o Regulamento Técnico Metrológico consolidado para instrumentos de pesagem não automáticos. Instituto Nacional de Metrologia, Qualidade e Tecnologia.
*Conferir a data e a página de publicação no DOU.*

[Laroca et al. 2022b] Laroca, R., Santos, M., Estevam, V., Luz, E., and Menotti, D. (2022). A first look at dataset bias in license plate recognition. In *Conference on Graphics, Patterns and Images (SIBGRAPI)*, pages 234–239.
*Conferir as páginas: elas vieram da memória. DOI confirmado: 10.1109/SIBGRAPI55357.2022.9991768. Como o artigo já tem [Laroca et al. 2022], esta vira "2022b" e a existente "2022a".*

[Laroca et al. 2023] Laroca, R., Estevam, V., Britto Jr., A. S., Minetto, R., and Menotti, D. (2023). Do we train on test data? The impact of near-duplicates on license plate recognition. In *International Joint Conference on Neural Networks (IJCNN)*, pages 1–8.
*Conferir os coautores e as páginas: vieram da memória. DOI confirmado: 10.1109/IJCNN54540.2023.10191584.*

[Leveson and Turner 1993] Leveson, N. G. and Turner, C. S. (1993). An investigation of the Therac-25 accidents. *Computer*, 26(7):18–41.

[Lubna et al. 2021] Lubna, Mufti, N., and Shah, S. A. A. (2021). Automatic number plate recognition: A detailed survey of relevant algorithms. *Sensors*, 21(9):3028.

[Meszaros 2007] Meszaros, G. (2007). *xUnit Test Patterns: Refactoring Test Code*. Addison-Wesley.

[Parnas 1972] Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. *Communications of the ACM*, 15(12):1053–1058.

[Peffers et al. 2007] Peffers, K., Tuunanen, T., Rothenberger, M. A., and Chatterjee, S. (2007). A design science research methodology for information systems research. *Journal of Management Information Systems*, 24(3):45–77.

[Percival 2009] Percival, C. (2009). Stronger key derivation via sequential memory-hard functions. In *BSDCan 2009*, Ottawa.

[Percival and Josefsson 2016] Percival, C. and Josefsson, S. (2016). The scrypt password-based key derivation function. RFC 7914, IETF.

[Shi et al. 2017] Shi, B., Bai, X., and Yao, C. (2017). An end-to-end trainable neural network for image-based sequence recognition and its application to scene text recognition. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, 39(11):2298–2304.

[Silva and Jung 2018] Silva, S. M. and Jung, C. R. (2018). License plate detection and recognition in unconstrained scenarios. In *European Conference on Computer Vision (ECCV)*, pages 580–596.

[Wazlawick 2014] Wazlawick, R. S. (2014). *Metodologia de Pesquisa para Ciência da Computação*. Elsevier, Rio de Janeiro, 2 edition.

---

## 3. Consideradas e não incluídas

Ficaram de fora porque **não consegui confirmar** os dados com segurança. Não cite estas sem conferir.

- **Huynh, Smith e Harder (2016)**, "Truck appointment systems: Where we are and where to go from here", *Transportation Research Record* nº 2548. O título e o volume foram confirmados; a lista de autores e o DOI, não. É uma boa revisão sobre agendamento de caminhões, se você conseguir conferir na SAGE/TRB.
- **"A flexible approach for automatic license plate recognition in unconstrained scenarios"** (*IEEE T-ITS*, 2022, IWPOD-NET). O resumo foi confirmado; os autores (provavelmente Silva e Jung), não.
- **OIML R 76-1:2006**: a recomendação internacional para instrumentos de pesagem não automáticos. Existe e está disponível no site da OIML, mas não li o texto. Para o artigo, o RTM do Inmetro já cumpre esse papel em contexto brasileiro.

## 4. Lacunas observadas

- **Trabalhos acadêmicos sobre balança rodoviária automatizada** continuam escassos. A busca encontrou basicamente o trabalho já citado [Agrawal and Joshi 2022], patentes e páginas comerciais. Isso reforça a afirmação da Seção 2.6, mas não é uma busca sistemática; não afirme que "não existem" trabalhos.
- **Nenhuma fonte acadêmica encontrada** avalia, em conjunto, LPR, agendamento e controle de cancelas com regras de falha segura. Essa conclusão vale só dentro desta busca.

---

*Declaração de uso de IA: levantamento assistido por IA (Claude Code com o plugin academic-research-skills). A escolha final e a leitura das fontes são do autor.*
