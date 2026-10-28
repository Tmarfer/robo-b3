# Robô B3 — Mini Índice (WIN) e Mini Dólar (WDO)

Laboratório de pesquisa para estratégias de day trade em WIN e WDO: dados, backtest em Python,
execução **simulada** no MT5 demo e, mais adiante, IA apenas para alertas e pausa de entradas.

> **Nesta fase o robô não envia ordens reais.** Qualquer operação real é manual e fora deste código.
> `config/risk.yaml` só aceita `modo: demo`.

- **Notas, histórico e decisões:** [Notion — Robô B3](https://app.notion.com/p/40678e338320818ba835ef415d26a273)
- **Código, scripts e infraestrutura:** este repositório

## Estrutura

```txt
robo-b3/
├── docs/
│   ├── roadmap.md            # fases, tarefas e critérios para avançar
│   ├── vps-setup.md          # passo a passo da VPS Hostinger + Antigravity via SSH
│   ├── mt5.md                # MT5 demo da Clear (Mac e VPS) + exportação de histórico
│   ├── fluxo-git.md          # como o código vai daqui → GitHub → VPS
│   └── estrategias/          # especificação escrita de cada estratégia ANTES do código
├── infra/vps/                # scripts numerados para preparar a VPS
├── scripts/                  # utilitários avulsos (ex.: mt5_exportar.py, requer Python Windows/Wine)
├── src/robob3/               # pacote Python (dados, instrumentos, sinais, config)
├── tests/                    # pytest
├── config/                   # risk.example.yaml (copiar para risk.yaml)
├── data/                     # raw/ e processed/ — fora do git
├── docker-compose.yml        # lab (padrão) e mt5 (perfil: MT5 demo no Wine, tela via túnel)
└── Dockerfile                # imagem do laboratório Python
```

## Começo rápido

Local (ou na VPS, fora do Docker):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test

# relatório de qualidade de um CSV exportado do MT5 (Símbolos > Barras > Exportar)
robob3 relatorio-dados data/raw/WIN_N_M1.csv

# gerar M5 a partir de M1
robob3 reamostrar data/raw/WIN_N_M1.csv --minutos 5 --saida data/processed/WIN_M5.parquet
```

Na VPS, via Docker:

```bash
make docker-build
docker compose run --rm lab relatorio-dados data/raw/WIN_N_M1.csv
```

## Onde estamos

Ver [docs/roadmap.md](docs/roadmap.md). Resumo: **Fase 0** (infra + repositório) e **Fase 1**
(levantar o histórico M1 disponível no MT5 da Clear e medir a qualidade).
