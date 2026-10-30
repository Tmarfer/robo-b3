# Gravador de M1 (Fase 4)

O servidor demo da Clear só entrega as **últimas 100 mil barras de M1 (~8,5 meses)**, e essa janela
anda todo dia. O gravador guarda o M1 em disco para o histórico não se perder.

## Como funciona

- Lê do MT5 que roda no container `mt5` (ponte RPyC na rede interna, porta 18812). **Só leitura.**
- Grava um Parquet por dia e por símbolo em `data/gravador/m1/{WIN-N|WDO-N}/AAAA-MM-DD.parquet`.
- Só grava **dias completos** (até ontem, horário de Brasília) e **nunca sobrescreve** um dia gravado.
- Na primeira execução puxa tudo o que o servidor tiver e **descarta o 1º dia**, cortado pelo limite.
- Cada execução acrescenta uma linha em `data/gravador/registro.jsonl` (servidor, conta demo, build,
  dias novos, barras, SHA-256 de cada arquivo, erros).

## Primeira execução (VPS)

```bash
cd ~/robo-b3 && git pull --ff-only && make docker-build && make docker-test
docker compose --profile mt5 up -d mt5            # se ainda não estiver no ar
docker compose ps                                  # mt5 precisa estar "healthy"
docker compose --profile mt5 run --rm coletor      # backfill: ~8,5 meses de WIN e WDO
docker compose run --rm lab gravador-status
```

Conferência: os dias gravados devem bater com o M1 exportado à mão em 29/10. Ex.:

```bash
docker compose run --rm lab gravador-exportar 'WIN$N' --saida data/processed/WIN-N_M1_gravador.csv
docker compose run --rm lab relatorio-dados data/processed/WIN-N_M1_gravador.csv
```

## Agendamento (cron do usuário robo)

```bash
crontab -e
# acrescentar:
15 8 * * 1-6  /home/robo/robo-b3/infra/vps/gravador-cron.sh
```

Log em `logs/gravador.log`. Código de saída diferente de zero = algum símbolo falhou (ver o log e o
`registro.jsonl`). Conferir de tempos em tempos com `gravador-status`: `dias_uteis_sem_gravar` deve
ficar em 0 ou 1.

## Limites conhecidos

- Se o gravador ficar parado mais de ~8,5 meses, os dias mais antigos saem da janela do servidor.
- Feriados não geram arquivo (não há barras). `dias_uteis_sem_gravar` conta feriados como dias úteis.
- Ticks e livro de ofertas ficam para depois (volume, licença e necessidade a avaliar).
