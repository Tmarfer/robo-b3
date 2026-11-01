# Tratamento dos dados — o que é feito e as regras para o que vier

> Conferido em 01/11/2026 contra duas pesquisas sobre robôs para WIN/WDO (séries contínuas,
> rolagem, look-ahead, custos e robustez). Vale para qualquer estratégia nova.

## Séries contínuas e rolagem

| Item | Como está | Onde |
| --- | --- | --- |
| Série | `WIN$N` / `WDO$N` da Clear (MT5), **não ajustadas**: o salto da troca aparece no preço | `data/raw/` |
| Datas de troca | WIN: 30 de 30 confirmadas (2021–2026), quarta mais próxima do dia 15 dos meses pares. WDO: último dia útil do mês; 39 confirmadas, 17 prováveis incluídas, 3 ainda pendentes | `config/rolagens.yaml` |
| Convenção | A 1ª barra da data listada já é do contrato novo | idem |
| Ajuste | Retroajuste **aditivo** (preserva pontos) ou **por razão** (preserva %), com a lista dos saltos aplicados | `src/robob3/data/rollover.py`, `robob3 ajustar-rolagem` |
| Preço de execução | Sempre da série **original**; a ajustada serve só para indicadores que atravessam dias | docstring de `rollover.py` |

**Regra para estratégias:**
1. Só usa dados do próprio dia e zera no mesmo dia (ex.: `win-orb-v1`): série original, sem ajuste. O
   salto da troca acontece entre dias e não afeta sinal nem resultado.
2. Usa informação de dias anteriores (máxima/mínima do dia anterior, topos, médias, ATR, gaps):
   **ou** a janela fica dentro do mesmo contrato e o dia da troca não opera (ex.: `win-pivo-v1`,
   testado em `tests/test_backtest_pivo.py::test_rolagem`), **ou** os indicadores vêm da série
   ajustada e a execução da original. Escolher na especificação, antes do teste.
3. Estratégia com WDO que atravesse dias: antes, resolver as 3 datas pendentes do WDO.
4. Nenhuma posição atravessa a noite, então a troca nunca cai no meio de uma operação.

## Outros pontos conferidos

| Ponto | Situação |
| --- | --- |
| Sem olhar o futuro | Sinais só com barras fechadas antes da entrada; linhas de referência só com pregões anteriores; contexto global só com o que existe às 08:30 (`docs/contexto-global.md`) |
| Fuso | Horário do servidor = Brasília; o Brasil não tem horário de verão desde 2019; saída por tempo às 17:00 fica antes de qualquer mudança no fechamento da B3 |
| Pregões incompletos | Pontas cortadas do arquivo descartadas; dias que abrem fora das 09:00 (ex.: Cinzas) não operam |
| Dados brutos | `data/raw/` nunca é editado; M1 gravado diariamente sem sobrescrever (`docs/gravador.md`) |
| Custos | R$ 0,25 por lado + 5 pts de derrapagem em entrada, stop e saída por tempo; sensibilidade com R$ 0,50 |
| Barras ambíguas | Regra conservadora (stop primeiro) e diagnóstico otimista; o M1 gravado servirá para conferir |
| Fora da amostra | 2026 congelado, roda uma vez só |
| Quantas configurações foram testadas | Registrado: cada rodada grava um manifesto com todas as combinações (`data/backtests/`) |

## A acrescentar quando uma estratégia passar no desenvolvimento

Testes de robustez sugeridos pelas pesquisas, a escrever na especificação antes de rodar:
derrapagem ×2; tirar os 5 e os 10 melhores pregões; atrasar a entrada em uma barra; parâmetros
±20%; resultado por mês, por ano e na semana da rolagem; e, com muitas combinações testadas, o
Sharpe deflacionado (Bailey e López de Prado).
