# Instruções para agentes na VPS (Codex, Antigravity e outros)

Projeto **Robô B3**: pesquisa de day trade em mini índice (WIN) e mini dólar (WDO). Hoje é
laboratório: dados, backtest e gravação de M1. **Nenhuma ordem é enviada**, nem em conta demo.

## Papéis

- **Thiago** decide.
- **Claude** escreve o código e as especificações, revisa os resultados e mantém o Notion.
- **Agente na VPS (você)** executa, valida e reporta. Pode corrigir infraestrutura (Docker, cron,
  permissões) e fazer commits pequenos e explicados. Mudança em regra de estratégia ou no motor de
  backtest: não faça, reporte.
- **Mesa B3** (Grok) só lê e dá pareceres.

## Regras que não mudam

1. **Nunca enviar ordens.** `config/risk.yaml` só aceita `modo: demo`.
2. **Período fora da amostra (02/01–29/10/2026) é intocado.** Nunca rodar `--periodo
   fora-da-amostra` nem usar `--confirmo-fora-da-amostra` sem pedido explícito do Thiago.
3. **Segredos:** `.env` e `config/risk.yaml` nunca vão para o git. Senha nunca em log, commit,
   relatório ou Notion. **Não procurar credenciais** em históricos de shell, do git ou de
   conversas: se faltar alguma, peça.
4. **VPS compartilhada:** não mexer em `hermes-dashboard`, `hermes-gateway`, `buzz-prod` nem no
   `ufw`. Portas novas só em `127.0.0.1` (acesso por túnel SSH). `sudo` só quando indispensável, e
   dizendo por quê.
5. **MT5:** não desmontar, alterar ou "consertar" o `terminal64.exe` nem usar chaves não
   documentadas no `common.ini`. A imagem é `infra/mt5/Dockerfile` (Wine ≥ 10); refazer só fora do
   pregão (09:00–18:30 de Brasília).
6. **Dados:** `data/raw/` nunca é editado. Divergência em número: não "conserte", reporte.
7. **Backtests** só via `infra/vps/lab.sh` (grava o manifesto com o hash do commit). Manifestos em
   `data/backtests/` são commitados e nunca apagados.

## Rotina

```bash
cd ~/robo-b3
git pull --ff-only
make docker-build && make docker-test          # tudo tem que passar antes de qualquer coisa
infra/vps/lab.sh <comando robob3> ...           # laboratório (backtest, dados)
docker compose --profile mt5 up -d mt5          # MT5 demo (tela: túnel SSH → localhost:8080)
docker compose --profile mt5 run --rm coletor   # gravador de M1 (cron: 15 8 * * 1-6)
```

Documentação: `docs/roadmap.md` (fases), `docs/mt5.md`, `docs/gravador.md`,
`docs/contexto-global.md`, `docs/estrategias/`.

## Commits

Mensagem em português dizendo o que mudou e por quê. Na `main` só o que passou em
`make docker-test`. Experimento ou mudança grande: branch própria, **com push**, e avise.

## Relatório ao final de cada tarefa

1. Commit em que a VPS ficou e saída do `make docker-test`.
2. O que foi feito, passo a passo, com as saídas relevantes (sem segredos).
3. O que deu errado, com a mensagem de erro exata e a causa provável (diga se é hipótese).
4. Qualquer arquivo alterado fora do git (`.env`, `mt5-data/`, cron) e por quê.
