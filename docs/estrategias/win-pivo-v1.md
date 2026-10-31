# Estratégia: Pivô nos extremos do dia anterior ("Sneaky Pivot") — WIN — v1

> Versão 1, escrita em 31/10/2026 **antes de qualquer teste**, a partir do vídeo "How Trading Like
> an Idiot Makes Me $10,000/Month" (canal The Rumers, setup "Sneaky Pivot"). As partes subjetivas
> do vídeo viraram regras objetivas abaixo. **Congelada em 31/10/2026** com as decisões do Thiago:
> saída às 17:00, mínimo de 100 operações e grade de 6 combinações. Mudou uma regra? Nova versão
> (v2…), com data e motivo.

## Hipótese

Os extremos do pregão anterior (máxima e mínima) e os topos e fundos anteriores logo além deles
concentram ordens grandes. Quando o preço testa um desses extremos nos primeiros 30 minutos e é
segurado, tende a voltar para dentro da faixa, em direção ao extremo oposto (reversão à média).

É o oposto da `win-orb-v1` (rompimento), que não mostrou vantagem nenhuma no WIN. O vídeo mostra
duas operações escolhidas em ações americanas; isso não é evidência. O título ("$10.000 por mês")
não entra na avaliação.

## Dados

- **Série:** `WIN$N`, servidor `ClearInvestimentos-DEMO`, M5, mesmo arquivo da v1
  (`data/raw/WIN-N_M5_clear-mt5_20261030.csv`, SHA-256 `c71792570d65…`).
- **Barras de sinal:** M15 montadas a partir do M5 (`robob3 reamostrar`). **Execução:** barras M5
  (entrada, stop e alvo verificados de 5 em 5 minutos, o que reduz a ambiguidade).
- **Rolagem:** série original, sem ajuste. **No pregão em que a série troca de contrato** (datas de
  `config/rolagens.yaml`) **não há operação**: a faixa do pregão anterior é de outro contrato. Os
  topos e fundos anteriores (swing) só são procurados dentro do contrato atual.
- **Desenvolvimento:** 31/03/2023 a 30/12/2025 (os primeiros pregões ficam sem operação até haver
  histórico para o swing). **Fora da amostra:** 02/01/2026 a 29/10/2026, uma única vez e só se o
  desenvolvimento aprovar. Mesmos períodos da v1, para comparar com a Estratégia de Referência.

## Definições

- **Faixa anterior:** `RH` (Range High) e `RL` (Range Low) = máxima e mínima do pregão anterior
  inteiro. Amplitude `A = RH − RL`.
- **Tolerância:** `T = TOL × A`, arredondada ao tick (5 pontos). Traduz o "não é milimétrico" do
  vídeo: toques perto da linha valem.
- **Pivô (topo/fundo) em M15:** barra cuja máxima é maior que a máxima das 2 barras M15 de cada lado
  (topo); idem com mínimas para fundo. Procurado nos últimos 10 pregões do mesmo contrato.
- **Swing High (`SH`):** o topo mais recente, antes do pregão de hoje, com máxima **acima de RH**.
  **Swing Low (`SL`):** o fundo mais recente com mínima **abaixo de RL**. Sem swing encontrado, o
  lado correspondente não opera no dia.
- **Zona compradora:** de `SL − T` até `RL + T`. **Zona vendedora:** de `RH − T` até `SH + T`.
  Entre as duas zonas (miolo) nunca há entrada.
- **Barras do dia (M15):** `B1` = 09:00–09:15, `B2` = 09:15–09:30, `B3` = 09:30–09:45. Pregão que
  não abre às 09:00 ou sem B1–B3 completas: sem operação.

## Regras

| Item | Regra (compra; a venda é o espelho) |
| --- | --- |
| Abertura | B1 abre **acima** de `SL − T` (não abriu já fora da zona). Abriu abaixo: sem operação nesse lado |
| Teste da zona | `mín(B1, B2) ≤ RL + T` (o preço chegou à zona compradora) |
| Zona defendida | Nem B1 nem B2 **fecham** abaixo de `SL − T` |
| Gatilho | Durante B3 (09:30–09:45), o preço atinge `máx(B2) + 5` (rompe a máxima da "vela sorrateira") |
| Cancelamento | Se, dentro de B3 e antes do gatilho, o preço for abaixo do stop, o setup é cancelado |
| Stop | `mín(B1, B2) − 5` (abaixo das mínimas testadas) |
| Alvo | `ALVO` × distância de `entrada` até `RH` (ver Parâmetros) |
| Saída por tempo | Abertura da barra M5 das 17:00, como na v1 (o vídeo segura até o fim do dia; 17:00 evita o fim do pregão e permite comparar) |
| Operações por dia | Uma. Se as duas zonas armarem (raro), vale o primeiro gatilho |
| Tamanho | 1 contrato |

Fica **fora** da v1, por ser discricionário: o "ajuste técnico" do vídeo para dias de abertura muito
volátil (usar a primeira vela de 15 min como subfaixa). Pode virar v2.

## Execução simulada no backtest (M5)

Igual à v1, para comparar: entrada no gatilho (ou na abertura da M5, se saltar), com **5 pontos de
derrapagem** contra; stop com 5 pontos contra; alvo como ordem limitada, sem derrapagem; saída por
tempo com 5 pontos contra; **R$ 0,25 por lado** (sensibilidade obrigatória com R$ 0,50).
Ambiguidade dentro de uma barra M5 (stop e alvo, ou entrada e stop): considera **stop**. Modo
otimista só como diagnóstico.

**Sanidade do motor (31/10/2026, antes do teste):** em 32 passeios aleatórios com 700 pregões cada,
refazendo as operações no caminho completo de preço (sem barras), o resultado médio foi zero
(+16,9 e −0,2 pontos por operação em dois lotes; t = 0,89 e −0,01), então o motor não fabrica
vantagem. O motor favorece de 10 a 13 pontos por operação ao executar o stop exatamente no preço
quando o preço passa do stop. No WIN, com ticks de 5 pontos, a derrapagem de 5 pontos cobre a maior
parte disso, mas em mercado rápido o salto pode ser maior. Isso vale também para a v1.

## Parâmetros

| Parâmetro | Valores | Observação |
| --- | --- | --- |
| `ALVO` | 0,5; 1,0 | metade do caminho até a borda oposta, ou a borda oposta inteira (`RH`) |
| `TOL` | 5%, 10%, 15% da amplitude anterior | quão perto da linha conta como teste |

**6 combinações.** Fixos: 2 barras de cada lado no pivô, 10 pregões de busca, B1–B3, 17:00.
Escolha final pela regra da v1: combinação do meio de uma região estável, nunca a melhor isolada.

## Comparação obrigatória

**Entrada aleatória:** nos mesmos dias, no mesmo horário e preço de entrada da estratégia, com
direção sorteada e as mesmas distâncias de stop e alvo; 1.000 sorteios. A estratégia precisa ficar
acima de 95% deles. Isso isola a pergunta certa: a direção escolhida pelo setup vale mais que uma
moeda?

## Critérios definidos antes do teste

**Desenvolvimento** (todos): 1) resultado líquido positivo; 2) fator de lucro ≥ 1,2;
3) pelo menos 100 operações (o setup é seletivo; 150, como na v1, poderia ser inalcançável sem
dizer nada sobre a vantagem); 4) positivo em 2 dos 3 anos; 5) região estável (a
escolhida e 2 vizinhas positivas); 6) acima de 95% da entrada aleatória; 7) positivo com custo de
R$ 0,50 por lado. **Fora da amostra:** uma vez só, resultado positivo e fator de lucro ≥ 1,1,
comparado com a Estratégia de Referência no mesmo período.

## Métricas a reportar

As da v1 (manifesto completo) e mais: nº de dias com setup armado e com gatilho, por lado;
resultado separado de compras e vendas; distribuição da distância de stop (em pontos); quantos dias
ficaram sem swing ou sem operação por rolagem.

## Resultado

**31/10/2026 — reprovada no desenvolvimento. Nenhuma combinação escolhida; o fora da amostra não
será rodado.**

Rodada: commit `5c37569`, dados SHA-256 `c71792570d65…`, 31/03/2023 a 30/12/2025, R$ 0,25 por
lado, 1.000 sorteios da entrada aleatória (semente 42). Manifestos:
`data/backtests/win-pivo-v1_desenvolvimento_conservadora_20261031-195230.json` e
`data/backtests/win-pivo-v1_desenvolvimento_otimista_20261031-195243.json`.

### Grade (modo conservador, o que vale)

| ALVO | TOL | Oper. | Resultado R$ | Com R$ 0,50 | Fator de lucro | Acerto | Expect. R$ | DD máx. R$ | 2023 | 2024 | 2025 | Percentil aleatório |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0,5 | 5% | 93 | −1.410,50 | −1.457,00 | 0,717 | 43,0% | −15,17 | −1.670,00 | −931,00 | −81,50 | −398,00 | 20,4 |
| 0,5 | 10% | 115 | −1.392,50 | −1.450,00 | 0,764 | 42,6% | −12,11 | −1.600,50 | −664,00 | −256,50 | −472,00 | 20,6 |
| 0,5 | 15% | 141 | −1.371,50 | −1.442,00 | 0,807 | 44,7% | −9,73 | −1.509,00 | −613,50 | −141,00 | −617,00 | 20,4 |
| 1,0 | 5% | 93 | −1.284,50 | −1.331,00 | 0,787 | 33,3% | −13,81 | −2.041,00 | −961,00 | −826,50 | +503,00 | 13,9 |
| 1,0 | 10% | 115 | −1.089,50 | −1.147,00 | 0,843 | 34,8% | −9,47 | −1.794,50 | −664,00 | −1.022,50 | +597,00 | 17,0 |
| 1,0 | 15% | 141 | −750,50 | −821,00 | 0,910 | 36,9% | −5,32 | −1.526,00 | −477,50 | −597,00 | +324,00 | 23,3 |

**Modo otimista (só diagnóstico):** melhora todas as linhas, mas só `ALVO 1,0 / TOL 15%` fica
positiva (+R$ 290,50; fator de lucro 1,036; percentil 43,3). As outras cinco continuam negativas
(−R$ 48,50 a −R$ 1.126,50); percentil de 24,2 a 43,3. Nem no modo otimista algum critério de
vantagem passaria.

### Os 7 critérios

| # | Critério | Resultado |
| --- | --- | --- |
| 1 | Resultado líquido positivo | **Não.** As 6 combinações negativas (−R$ 750,50 a −R$ 1.410,50) |
| 2 | Fator de lucro ≥ 1,2 | **Não.** Máximo 0,910 |
| 3 | ≥ 100 operações | Sim para TOL 10% e 15% (115 e 141); não para TOL 5% (93) |
| 4 | Positivo em 2 dos 3 anos | **Não.** ALVO 1,0 só ganha em 2025; ALVO 0,5 perde nos três anos |
| 5 | Região estável (escolhida e 2 vizinhas positivas) | **Não.** Não há nenhuma combinação positiva, logo não há região a escolher |
| 6 | Acima de 95% da entrada aleatória | **Não.** Percentil de 13,9 a 23,3 |
| 7 | Positivo com R$ 0,50 por lado | **Não.** Todas negativas (−R$ 821,00 a −R$ 1.457,00) |

Pela regra da especificação (combinação do meio de uma região estável), **não há combinação a
escolher**. Seis de sete critérios falham em todas as combinações.

### Métricas pedidas pela especificação (modo conservador)

- **Pregões:** 687 no período: 17 sem operação por rolagem, 1 sem histórico (primeiro pregão) e
  669 avaliados; destes, 4 não abriram às 09:00 e 2 não tinham B1–B3 completas.
- **Sem swing** (independe de ALVO e TOL): sem `SH` em 182 pregões, sem `SL` em 164, sem os dois
  em 21.
- **Setups armados e com gatilho, por lado** (armado = gatilho + sem gatilho + cancelado; nenhum
  dia teve os dois lados armados sem gatilho):

  | TOL | Compra: armados / gatilho | Venda: armados / gatilho | Sem setup |
  | --- | --- | --- | --- |
  | 5% | 91 / 46 | 94 / 47 | 478 |
  | 10% | 116 / 57 | 115 / 58 | 432 |
  | 15% | 139 / 65 | 144 / 76 | 380 |

  Cerca de metade dos setups armados não chega a disparar (sem gatilho ou cancelado no stop).
- **Compras × vendas (R$):** as duas pontas perdem em todas as combinações. ALVO 0,5:
  compras −812,00 / −900,50 / −756,50, vendas −598,50 / −492,00 / −615,00 (TOL 5/10/15%).
  ALVO 1,0: compras −704,00 / −590,50 / −454,50, vendas −580,50 / −499,00 / −296,00.
- **Distância do stop** (do preço de gatilho até o stop, em pontos): mínima 150, quartis
  ~315–350 / 450–490 / 600–640, máxima 1.270. O stop é largo: a mediana (~450 pontos, R$ 90) é
  quase a perda média por operação (R$ 89–97).
- **Saídas** (ALVO 1,0 / TOL 10%): 70 no stop, 25 no alvo, 20 por tempo.
- **Barras ambíguas:** 8 a 13 por combinação; trocá-las de stop para alvo (modo otimista) muda
  R$ 284 a R$ 1.041 no total, mas não muda a conclusão.

### Leitura

- A reversão nos extremos do pregão anterior, do jeito objetivo que a v1 a definiu, **não mostrou
  vantagem no WIN** em 2023–2025: perde nas duas pontas, perde nos três anos com ALVO 0,5, e a
  direção escolhida pelo setup fica abaixo da mediana da moeda (percentil 14–23).
- Ficar abaixo da mediana **não** é evidência de que o contrário (seguir o rompimento) funcione:
  para isso o percentil teria de ficar abaixo de 5, e a `win-orb-v1` (rompimento) também já foi
  reprovada.
- A única linha positiva aparece no modo otimista, na ponta da grade (ALVO e TOL máximos), sem
  vizinhas positivas: é exatamente o tipo de resultado que a regra de escolha manda ignorar.
- **Próximo passo:** decisão do Thiago. A v1 está encerrada; o fora da amostra (2026) continua
  intocado. Uma v2 (por exemplo, o "ajuste técnico" para aberturas voláteis, deixado de fora) só
  com nova especificação, congelada antes do teste, e sabendo que cada nova tentativa no mesmo
  período de desenvolvimento aumenta o risco de achar vantagem por acaso.
