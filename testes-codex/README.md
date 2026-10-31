# Testes Codex

O primeiro experimento está descrito em `rompimento-v1.md`. Para refazer a rodada no
Mac, com o código commitado e no ambiente `.venv`:

```sh
.venv/bin/robob3 backtest-codex-rompimento data/raw/WIN-N_M5_clear-mt5_20261030.csv
```

O comando gera um manifesto versionável em `data/backtests/` e um arquivo local
`resultado.json` com operações e barras do desenvolvimento. O resultado local e a
pasta `painel/` são ignorados pelo Git porque contêm dados derivados do CSV bruto.
O arquivo local `Painel-WIN.html` abre diretamente no navegador, sem servidor. Basta
dar dois cliques nele no Finder. Ele contém uma fotografia das rodadas e não se
atualiza sozinho ao executar novos testes. É ignorado pelo Git porque contém dados
derivados dos CSVs. `DashboardContent.jsx` e `dashboard.css` guardam a interface.

As três ideias de médias, MACD e estocástico e os recortes usados estão detalhados em
`fichas-v1.md`. Os nove manifestos da grade ficam em `data/backtests/`; o resultado
detalhado de operações e a cópia de segurança anterior à correção permanecem locais.
O painel reúne essas três ideias e o rompimento anterior. Os recortes em 2026 são
exploratórios; outubro não faz parte dos testes.

O teste é exploratório. A rodada de janeiro a setembro de 2026 foi autorizada
explicitamente por Thiago e registrada separadamente como fora da amostra; outubro
de 2026 continua reservado. Uma nova regra precisa de nova especificação e de um novo
manifesto antes de ser comparada com esta.
