# Fluxo de código

```txt
 você (Antigravity / Claude Code)  ──push──▶  GitHub (privado)  ──pull──▶  VPS ~/robo-b3
                                              │
                                              └── Actions: ruff + pytest a cada push/PR
```

**O GitHub é a fonte da verdade.** A VPS só recebe código pelo `git pull`.

## Branches

- `main` — sempre passa nos testes; é o que roda na VPS.
- `feat/<assunto>` — trabalho em andamento (ex.: `feat/relatorio-dados`, `feat/backtest-base`).
  Abrir PR para `main`; o CI precisa ficar verde antes do merge.

## Duas formas de trabalhar

1. **Editar direto na VPS pelo Antigravity** (Remote-SSH): commit e push saem da VPS usando a sua
   chave via `ForwardAgent` — nada de chave pessoal gravada no servidor.
2. **Editar em outro lugar** (seu PC, Claude Code na nuvem): push para o GitHub e na VPS
   `bash infra/vps/deploy.sh`.

Não misturar as duas na mesma branch ao mesmo tempo, para evitar conflito.

## O que nunca vai para o git

`.env`, `config/risk.yaml`, `data/raw/`, `data/processed/`, `logs/`, `mt5-data/`.
Dados de mercado podem ter restrição de licença; ficam na VPS e no backup.

## Registro no Notion

Cada fase concluída, decisão ou resultado de teste vira uma entrada no Notion com o link do commit
ou PR correspondente. O código registra *como*; o Notion registra *por quê* e *o que aprendemos*.
