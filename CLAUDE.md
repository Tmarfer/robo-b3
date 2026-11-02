# Robô B3 — instruções para o Claude Code (sessão local no Mac)

@AGENTS.md

As regras do `AGENTS.md` (acima) valem aqui também. Este arquivo acrescenta o que é específico do
Mac e o estado do projeto. Escreva sempre em português do Brasil, com linguagem simples: o Thiago
decide, e cada resposta deve deixar claro o que foi feito, o que deu certo e o que não deu.

## Divisão de trabalho (desde 31/10/2026)

- **Mac (esta sessão):** pesquisa, especificação e backtest. Rodar direto, conferir e corrigir.
- **VPS (Codex):** só o que precisa ficar ligado: MT5 demo, gravador diário de M1 e, mais adiante,
  a operação em conta demo durante o pregão (Fase 5). Tarefas para o Codex são escritas aqui e
  coladas pelo Thiago.
- **Notion:** diário e acompanhamento. Atualizar a cada evento relevante, sem detalhe demais:
  o que foi feito, o que deu certo e o que não deu. O Mesa B3 (Grok) lê o Notion e dá pareceres.

## Ambiente no Mac

```bash
cd ~/Projetos/robo-b3 && source .venv/bin/activate
git pull --ff-only && pytest -q        # tudo passando antes de qualquer coisa
# dados (fora do git) vêm da VPS:
scp 'robo-b3:~/robo-b3/data/raw/*.csv' data/raw/
rsync -av robo-b3:~/robo-b3/data/gravador/ data/gravador/
```

Backtest: commitar o código antes (o manifesto registra o commit) e depois commitar o manifesto:
```bash
robob3 backtest-pivo data/raw/WIN-N_M5_clear-mt5_20261030.csv --grade
robob3 backtest-pivo data/raw/WIN-N_M5_clear-mt5_20261030.csv --grade --ambiguidade otimista
git add data/backtests/*.json && git commit -m "Manifestos ..." && git push
```
Só o período de desenvolvimento. Fora da amostra (2026) só com pedido explícito do Thiago.

## Estado em 31/10/2026

- **Fases 0–2:** concluídas. **Fase 3 (atual):** win-orb-v1 reprovada (18 linhas no DB Backtests,
  percentil contra o aleatório de 0 a 56). **win-pivo-v1** ("Sneaky Pivot", reversão nos extremos do
  pregão anterior) **reprovada em 31/10/2026**: as 6 combinações perdem no modo conservador, falham
  6 dos 7 critérios, percentil 13,9–23,3 (resultado em `docs/estrategias/win-pivo-v1.md`, 12 linhas
  no DB Backtests). **Próximo passo: o Thiago decide a próxima hipótese.**
- **Fase 4:** gravador de M1 funcionando na VPS (cron 08:15 seg–sáb). O MT5 **não volta logado
  sozinho** depois de reiniciar ou recriar o container: logar pela tela (noVNC) depois de cada
  reinício. Solução em três camadas (Wine num volume, desligamento limpo, aviso às 08:00) na
  branch `fix/mt5-login-definitivo`, aguardando o teste do Codex
  (`infra/vps/tarefas/2026-11-01-login-definitivo.md`).
- **Dados:** tratamento conferido em 01/11 (rolagem, look-ahead, custos). Regras para estratégias
  que usam dias anteriores e testes de robustez a especificar: `docs/dados.md`.
- **Contexto global:** definição congelada em `docs/contexto-global.md` (z-score de 60 pregões);
  coletor das 08:30 e histórico ainda não escritos — depois de haver estratégia com vantagem.

## Notion

- Página do projeto: https://app.notion.com/p/40678e338320818ba835ef415d26a273 (diário, roadmap)
- Base de Conhecimento — Mesa B3: https://app.notion.com/p/40978e338320819d9742d5e099ed5c72
- DB Backtests: https://app.notion.com/p/1507031404b649b1b24bb176c3146bf7
  (data source `collection://95b16088-112c-442a-8471-a3648585f445`; uma linha por combinação,
  números copiados do manifesto, Fonte dos números = Manifesto)
- Fichas de Estratégia: https://app.notion.com/p/78a71d2cc14b4cd99da485014de8a7f3
  (win-pivo-v1: https://app.notion.com/p/40a78e33832081f08a7acf987b487eb5)
- Pareceres do Mesa: https://app.notion.com/p/f875c4c3a68747d9a8fd6130ddd6f771
