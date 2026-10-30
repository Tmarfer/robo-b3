# Estratégia: Rompimento da faixa de abertura (ORB) — WIN — v1

> Versão 1, escrita em 30/10/2026 **antes de qualquer teste**. **Congelada em 30/10/2026**, após a
> revisão (esclarecimentos: preço de referência em salto, entrada e alvo na mesma barra, dia sem barra
> das 17:00, faixa incompleta e custo da B3). Mudou uma regra? Nova versão (v2…) com data e motivo.

## Hipótese

Nos primeiros minutos do pregão o mercado absorve a informação acumulada desde o fechamento
anterior. Quando o preço sai da faixa desses minutos, o movimento tende a continuar por parte do
dia, mais do que voltar.

É uma ideia conhecida e muito testada. Não há expectativa de que funcione: o objetivo da v1 é
**testar a hipótese com custos realistas** e ter uma base de comparação para as próximas
estratégias. Resultado negativo é um resultado válido.

## Dados

- **Série:** `WIN$N`, servidor `ClearInvestimentos-DEMO`, M5, arquivo
  `data/raw/WIN-N_M5_clear-mt5_20261030.csv` (SHA-256 `c71792570d658f216067d9e1c08d18d6209732eec23535353a4c2be4eeb7d392`).
- **Rolagem:** série original, **sem ajuste**. A estratégia só usa dados do próprio dia e zera
  antes do fechamento, então o salto de rolagem entre dias não afeta sinais nem resultado.
- **Desenvolvimento:** 31/03/2023 a 30/12/2025 (o 30/03/2023 é cortado no meio do pregão).
- **Fora da amostra (não olhar até o fim do desenvolvimento):** 02/01/2026 a 29/10/2026.
  Inclui as segundas-feiras após os dois turnos da eleição (05/10 e 26/10).
- **M1** (02/2026 em diante) só existe dentro do período fora da amostra: serve para conferir, nessa
  avaliação final, a ordem real de stop e alvo nas barras M5 ambíguas.

## Definições

- **Faixa de abertura (FA):** máxima e mínima das 3 primeiras barras M5 do dia (09:00, 09:05 e
  09:10, ou seja, 09:00–09:15).
- **Tick do WIN:** 5 pontos. Valor do ponto: R$ 0,20 por contrato.
- **Gatilho de compra:** máxima da FA + 5 pontos. **Gatilho de venda:** mínima da FA − 5 pontos.
- **Preço de referência da entrada:** o gatilho; se a barra que dispara abrir além dele (salto), a
  abertura dessa barra. Stop e alvo são medidos a partir dele, para o risco ser sempre `STOP` pontos.

## Regras

| Item | Regra |
| --- | --- |
| Dias operáveis | Pregões que abrem às 09:00 com as 3 barras da FA presentes. Pregões que abrem mais tarde (ex.: Quarta-feira de Cinzas às 13:00), com barra faltando entre 09:00 e 09:10, ou cortados nas pontas da base: **sem operação** |
| Horário de entradas | Da barra das 09:15 até a barra das 11:55 (última barra que pode disparar entrada) |
| Sinal de compra | Preço atinge o gatilho de compra dentro da janela de entradas |
| Sinal de venda | Preço atinge o gatilho de venda dentro da janela de entradas |
| Operações por dia | **Uma.** Vale o primeiro gatilho atingido; depois dela, nenhuma nova entrada, nem virada de mão |
| Stop | Fixo: `STOP` pontos contra, medido a partir do preço de referência da entrada |
| Alvo | Fixo: `ALVO` × `STOP` pontos a favor, medido a partir do preço de referência da entrada |
| Saída por tempo | Se nem stop nem alvo forem atingidos, zera na abertura da barra das 17:00. Sem barra das 17:00 (pregão encerrado antes), zera no fechamento da última barra do dia |
| Tamanho | 1 contrato |
| Perda máxima diária | Uma operação por dia: `STOP` + 10 pontos de derrapagem + R$ 0,50 de custos ≈ R$ 32,50 (stop 150) a R$ 62,50 (stop 300), mais o que o preço saltar além do stop |

## Execução simulada no backtest (barras M5)

- **Entrada:** no preço de referência (gatilho, ou abertura da barra em caso de salto), mais
  **5 pontos de derrapagem contra**. A derrapagem afeta só o preço executado, não stop e alvo.
- **Stop:** no preço do stop; se a barra abrir além dele, na abertura. Derrapagem de **5 pontos
  contra**.
- **Alvo:** ordem limitada, no preço do alvo, sem derrapagem. Se a barra abrir além do alvo, sai na
  abertura (a favor).
- **Saída por tempo:** abertura da barra das 17:00 (ou fechamento da última barra do dia, se não
  houver a das 17:00), derrapagem de 5 pontos contra.
- **Os dois gatilhos na mesma barra:** entra no lado mais próximo da abertura da barra. Se o stop
  desse lado também estiver dentro da barra, considera **stop** (perda).
- **Stop e alvo na mesma barra:** considera **stop** (conservador).
- **Entrada e stop na mesma barra:** considera stop, na mesma barra.
- **Entrada e alvo na mesma barra, sem tocar o stop:** alvo executado na própria barra (para chegar
  ao alvo, o preço passa antes pelo gatilho, que fica do mesmo lado).
- **Custo por contrato:** **R$ 0,25 por lado** (tabela da B3 para day trade de minicontrato de
  índice, pessoa física: emolumentos ~R$ 0,16 + registro ~R$ 0,09, levantado em 30/10/2026;
  corretagem zero na Clear com RLP ativo). Confirmar na primeira nota de corretagem. Sensibilidade
  obrigatória com **R$ 0,50 por lado**. Impostos ficam fora desta avaliação.
- **Rolagem:** nenhuma regra especial; o dia da troca é operado normalmente.

## Parâmetros

| Parâmetro | Valores testados | Observação |
| --- | --- | --- |
| `STOP` | 150, 200, 300 pontos | R$ 30, 40 e 60 por contrato |
| `ALVO` (múltiplo do stop) | 1,5; 2; 3 | Alvo de 225 a 900 pontos |

São **9 combinações**, de propósito poucas. Faixa de abertura (15 min), janela de entradas e saída por
tempo **ficam fixas** na v1. A escolha final não é a melhor combinação, e sim uma combinação do
meio de uma região estável (vizinhas também positivas). Se só uma combinação isolada funcionar, a
hipótese é considerada **não confirmada**.

## Comparação obrigatória

**Entrada aleatória:** nos mesmos dias, às 09:15, direção sorteada (compra ou venda), mesmos stop,
alvo, saída e custos; 1.000 sorteios. A estratégia só mostra vantagem se o resultado dela ficar
acima de 95% dos sorteios.

## Critérios definidos antes do teste

**Desenvolvimento (2023–2025): segue para fora da amostra se tudo abaixo for verdade:**

1. Resultado líquido positivo depois de custos e derrapagem.
2. Fator de lucro (ganhos ÷ perdas) ≥ 1,2.
3. Pelo menos 150 operações.
4. Resultado positivo em pelo menos 2 dos 3 anos (2023 parcial, 2024, 2025).
5. Região estável: a combinação escolhida e pelo menos 2 vizinhas com resultado positivo.
6. Acima de 95% dos sorteios de entrada aleatória.
7. Resultado líquido continua positivo com custo de R$ 0,50 por lado (sensibilidade).

**Fora da amostra (2026): rodar uma única vez**, com a combinação escolhida e sem ajustes:

1. Resultado líquido positivo e fator de lucro ≥ 1,1.
2. Mostrar o resultado **com e sem** 05/10 e 26/10 (dias seguintes à eleição).
3. Com o M1, refazer as barras ambíguas e mostrar o quanto a hipótese conservadora mudou o resultado.

Se o desenvolvimento reprovar, **não** se testa fora da amostra: registrar no Notion e escrever a
próxima hipótese (nova estratégia ou v2, com o motivo da mudança).

## Métricas a reportar

Resultado líquido (pontos e R$), número de operações, taxa de acerto, ganho médio e perda média,
fator de lucro, expectativa por operação, maior sequência de perdas, drawdown máximo (R$), resultado
por ano e por mês, dias sem operação e motivo, número de barras ambíguas e como foram tratadas.

## Exemplo para conferência à mão

Barras do dia (fictícias): 09:00 → máx. 125.000 / mín. 124.700; 09:05 → máx. 124.950 / mín. 124.600;
09:10 → máx. 124.980 / mín. 124.650. Com `STOP` = 200 e `ALVO` = 2:

- FA: máxima 125.000, mínima 124.600. Gatilhos: compra 125.005, venda 124.595.
- Barra 09:25 atinge 125.040 → **compra**, preenchida a 125.005 + 5 = 125.010.
- Stop em 125.005 − 200 = 124.805; alvo em 125.005 + 400 = 125.405.
- Barra 10:40 atinge 125.420 → **alvo**, saída a 125.405.
- Resultado: 125.405 − 125.010 = **+395 pontos** = R$ 79,00 − R$ 0,50 de custos = **R$ 78,50**
  (R$ 78,00 na sensibilidade com R$ 0,50 por lado).
- Variação com salto: se a barra das 09:25 tivesse **aberto** a 125.080, a entrada seria 125.080 + 5 =
  125.085, com stop em 124.880 e alvo em 125.480 (medidos a partir de 125.080).

## Resultado

A preencher depois do backtest (Fase 3), com link para o relatório e para a página no Notion.
