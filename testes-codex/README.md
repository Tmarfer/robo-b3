# Testes Codex

O primeiro experimento está descrito em `rompimento-v1.md`. Para refazer a rodada no
Mac, com o código commitado e no ambiente `.venv`:

```sh
.venv/bin/robob3 backtest-codex-rompimento data/raw/WIN-N_M5_clear-mt5_20261030.csv
```

O comando gera um manifesto versionável em `data/backtests/` e um arquivo local
`resultado.json` com operações e barras do desenvolvimento. O resultado local e a
pasta `painel/` são ignorados pelo Git porque contêm dados derivados do CSV bruto.
O painel gerado usa uma fotografia dessa rodada; rodar novamente não o atualiza sozinho.
`DashboardContent.jsx` e `dashboard.css` guardam o conteúdo do painel gerado.

O teste é exploratório e opera apenas no histórico de desenvolvimento. Uma nova regra
precisa de nova especificação e de um novo manifesto antes de ser comparada com esta.
