# Análise por contrato — WIN em 2025

Análise exploratória de dois trechos completos da série contínua WIN$N da Clear, que cobrem março a maio de 2025. Pela convenção de `config/rolagens.yaml`, a primeira barra da data de troca já pertence ao contrato seguinte:

- 12/02/2025 a 15/04/2025;
- 16/04/2025 a 17/06/2025.

Esses são intervalos observados na série contínua; não estabelecem toda a vida ou o volume dos contratos individuais. A fonte de desenvolvimento é o CSV M5 local. As operações foram agrupadas pela data de entrada; os valores são em reais por contrato, com os custos e hipóteses das respectivas especificações.

| Estratégia e tempo | 12/02–15/04: operações / R$ | 16/04–17/06: operações / R$ |
| --- | ---: | ---: |
| Médias 5/20, M5 | 308 / -1.474,00 | 309 / -2.426,50 |
| MACD 12/26/9, M5 | 377 / -979,50 | 350 / -1.997,00 |
| Estocástico 14/3/3, M5 | 211 / -1.586,50 | 194 / -1.758,00 |
| Fibogap, M5, saída padrão | 13 / -47,50 | 12 / -196,00 |
| Pivô 1-2-3 Fibonacci, M5, saída padrão | 31 / +13,50 | 35 / -1.033,50 |
| Fibonacci duas etapas, M5, saída padrão | 7 / +127,50 | 5 / +2,50 |
| Retração 38–50%, M5, saída padrão | 17 / -435,50 | 14 / -231,00 |
| Rompimento e reteste, sinal M15 / execução M5 | 10 / -253,00 | 12 / -61,00 |

As três primeiras linhas foram agrupadas a partir de `testes-codex/resultado-fichas.json`; as quatro seguintes, de `testes-codex/resultado-fibonacci-tempos.json`. São operações já registradas nas rodadas anteriores, **não novos backtests isolados**; cada arquivo associa as operações aos manifestos de desenvolvimento existentes em `data/backtests/`. O painel local e os JSONs detalhados são ignorados pelo Git por conterem dados derivados dos CSVs.

A última linha é da nova execução de `robob3 backtest-codex-reteste`, que roda todo o desenvolvimento de 03/04/2023 a 30/12/2025. O manifesto é `data/backtests/win-codex-reteste-media-v1_desenvolvimento-exploratorio_conservadora_20261101-140009.json`. As 174 operações reproduziram exatamente o arquivo anterior, preservado em `testes-codex/backup-local/resultado-reteste-v1-antes-rolagem.json`. A tabela filtra essas operações, sem executar isoladamente cada contrato.

## Verificação da rolagem

- Médias, MACD e estocástico calculam indicadores agrupados pelas datas de troca, reiniciando o histórico em cada contrato (`codex_fichas.sinais`).
- O reteste agrupa a média exponencial por contrato e pula o dia de troca ao usar os níveis do pregão anterior (`codex_reteste`).
- Fibogap usa referência do pregão anterior; o simulador Fibonacci pula as datas de troca. Pivô, duas etapas e retração também passam por esse filtro, ainda que seus sinais sejam intradiários.
- O rompimento simples e o falso rompimento analisam barras dentro do dia; sua comparação não foi incluída na tabela.

Essas proteções e a segmentação não provam que os resultados estejam livres de outros problemas. O corte em contratos da série contínua não substitui dados dos contratos individuais. As hipóteses de execução, custos e ambiguidades continuam relevantes; resultados com poucos negócios são especialmente instáveis. Em particular, a separação dos contratos não altera os negócios já calculados e não demonstra quanto a rolagem afetaria uma implementação que a ignorasse. Para isso, seria necessária uma comparação controlada, especificada antes da execução.
