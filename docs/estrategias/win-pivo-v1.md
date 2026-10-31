# Estratégia: Pivô nos extremos do dia anterior ("Sneaky Pivot") — WIN — v1

> **RASCUNHO — não congelada.** Escrita em 31/10/2026, antes de qualquer teste, a partir do vídeo
> "How Trading Like an Idiot Makes Me $10,000/Month" (canal The Rumers, setup "Sneaky Pivot").
> As partes subjetivas do vídeo viraram regras objetivas abaixo; itens marcados **[DECIDIR]**
> esperam o Thiago. Depois de congelada, mudar uma regra = nova versão (v2…), com data e motivo.

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
| Saída por tempo | Abertura da barra M5 das 17:00 (como na v1). **[DECIDIR]** o vídeo segura até o fim do dia |
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
3) **pelo menos 100 operações [DECIDIR]** (o setup é seletivo, então 150 como na v1 pode ser
inalcançável sem dizer nada sobre a vantagem); 4) positivo em 2 dos 3 anos; 5) região estável (a
escolhida e 2 vizinhas positivas); 6) acima de 95% da entrada aleatória; 7) positivo com custo de
R$ 0,50 por lado. **Fora da amostra:** uma vez só, resultado positivo e fator de lucro ≥ 1,1,
comparado com a Estratégia de Referência no mesmo período.

## Métricas a reportar

As da v1 (manifesto completo) e mais: nº de dias com setup armado e com gatilho, por lado;
resultado separado de compras e vendas; distribuição da distância de stop (em pontos); quantos dias
ficaram sem swing ou sem operação por rolagem.

## Resultado

Preenchido depois do teste.
