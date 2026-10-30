# Estratégia: Rompimento da faixa de abertura (ORB) — WIN — v1

> Versão 1, escrita em 30/10/2026 **antes de qualquer teste**. Mudou uma regra? Nova versão (v2…)
> com data e motivo. Não alterar este arquivo depois que o backtest de desenvolvimento rodar.

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

## Regras

| Item | Regra |
| --- | --- |
| Dias operáveis | Pregões que abrem às 09:00. Pregões que abrem mais tarde (ex.: Quarta-feira de Cinzas às 13:00) ou que estão incompletos na base: **sem operação** |
| Horário de entradas | Da barra das 09:15 até a barra das 11:55 (última barra que pode disparar entrada) |
| Sinal de compra | Preço atinge o gatilho de compra dentro da janela de entradas |
| Sinal de venda | Preço atinge o gatilho de venda dentro da janela de entradas |
| Operações por dia | **Uma.** Vale o primeiro gatilho atingido; depois dela, nenhuma nova entrada, nem virada de mão |
| Stop | Fixo: `STOP` pontos contra, medido a partir do gatilho |
| Alvo | Fixo: `ALVO` × `STOP` pontos a favor, medido a partir do gatilho |
| Saída por tempo | Se nem stop nem alvo forem atingidos, zera na abertura da barra das 17:00 |
| Tamanho | 1 contrato |
| Perda máxima diária | Uma operação por dia: `STOP` + 10 pontos de derrapagem + R$ 1 de custos ≈ R$ 33 (stop 150) a R$ 63 (stop 300), mais o que o preço saltar além do stop |

## Execução simulada no backtest (barras M5)

- **Entrada:** no gatilho. Se a barra abrir além do gatilho (salto), entra na **abertura** da barra.
  Derrapagem de **5 pontos contra** em toda entrada.
- **Stop:** no preço do stop; se a barra abrir além dele, na abertura. Derrapagem de **5 pontos
  contra**.
- **Alvo:** ordem limitada, no preço do alvo, sem derrapagem. Se a barra abrir além do alvo, sai na
  abertura (a favor).
- **Saída por tempo:** abertura da barra das 17:00, derrapagem de 5 pontos contra.
- **Os dois gatilhos na mesma barra:** entra no lado mais próximo da abertura da barra. Se o stop
  desse lado também estiver dentro da barra, considera **stop** (perda).
- **Stop e alvo na mesma barra:** considera **stop** (conservador).
- **Entrada e stop na mesma barra:** considera stop, na mesma barra.
- **Custo por contrato:** R$ 0,50 por lado (emolumentos e taxas; corretagem de minicontratos na
  Clear considerada zero). Conferir com a tabela da B3 e a primeira nota de corretagem. Impostos
  ficam fora desta avaliação.
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
- Resultado: 125.405 − 125.010 = **+395 pontos** = R$ 79,00 − R$ 1,00 de custos = **R$ 78,00**.

## Resultado

A preencher depois do backtest (Fase 3), com link para o relatório e para a página no Notion.
