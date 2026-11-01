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

As versões com stop móvel dessas três ideias estão em `fichas-trailing-v2.md`.
No painel, a opção “Saída” alterna entre o stop móvel e o alvo fixo original; a
comparação informa também as operações sujeitas a ambiguidade dentro da barra.

As adaptações das três fichas de Fibonacci estão em `fibonacci-v1.md`. O painel
apresenta as saídas estruturais e com trailing para as mesmas entradas, sem
interpretar 2026 como validação independente.

O rompimento falso com trailing está em `rompimento-falso-v2.md`. A primeira rodada
de interpolação linear é inválida para avaliação e está preservada apenas para auditoria.
O painel mostra o diagnóstico com entrada na barra seguinte e hipótese adversa;
ele não reproduz a sequência real dos negócios e não comprova a execução intrabar.

A hipótese `reteste-media-v1.md` usa sinal M15 e execução M5 no desenvolvimento.
No painel, escolha “Rompimento e reteste · M15/M5” para ver as operações, o nível
do pregão anterior e a MME20 das barras M15 fechadas. A primeira rodada teve uma
contagem de saídas por horário incorreta; os dois manifestos estão preservados.

O teste é exploratório. A rodada de janeiro a setembro de 2026 foi autorizada
explicitamente por Thiago e registrada separadamente como fora da amostra; outubro
de 2026 continua reservado. Uma nova regra precisa de nova especificação e de um novo
manifesto antes de ser comparada com esta.
