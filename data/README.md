# Dados

`raw/` e `processed/` ficam **fora do git** (volume e licença). Vivem na VPS e no backup.

- `raw/` — arquivos como recebidos, nunca editados. Nome sugerido:
  `{SIMBOLO}_{TF}_{ORIGEM}_{AAAAMMDD-extracao}.csv`, ex.: `WIN$N_M1_clear-mt5_20261030.csv`
- `processed/` — derivados (sem pregões incompletos, M5, M15, Parquet), sempre regeneráveis a
  partir de `raw/`.

Para cada arquivo em `raw/`, registrar no Notion (seção 4.1) a saída de
`robob3 relatorio-dados ARQUIVO`: SHA-256, primeira/última barra, pregões, lacunas, duplicados —
mais servidor, símbolo, fuso do servidor e data da extração.

`backtests/` **é versionado**: um manifesto JSON por rodada de `robob3 backtest-orb` (commit, SHA-256
dos dados, custos, modo de ambiguidade, trecho e uma linha por combinação). Nunca apagar um
manifesto, nem os de rodadas ruins: é o histórico do que foi testado. Rodar na VPS com
`infra/vps/lab.sh backtest-orb ...` para o hash do commit entrar no arquivo.
