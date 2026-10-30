# Roadmap

Fases derivadas do plano no Notion (seções 5, 6 e "Etapas e critérios para avançar").
Cada fase só termina quando o **critério de saída** for cumprido e registrado no Notion.
Prazos são estimativas, não compromissos.

---

## Fase 0 — Infraestrutura e repositório ✅ concluída em 29/10/2026

- [x] Criar repositório privado `robo-b3` no GitHub e subir este código
- [x] VPS: rodar `infra/vps/00-bootstrap.sh` (usuário, SSH por chave, firewall, fuso, swap)
- [x] Confirmar login `ssh robo-b3` (alias) **antes** de fechar a sessão root
- [x] Antigravity conectado via Remote-SSH no alias `robo-b3`
- [x] VPS: `01-docker.sh`, `02-github.sh`, clonar o repo
- [x] VPS: `03-diagnostico.sh` → resultado no Notion (sem virtualização aninhada; 7,8 GiB RAM)
- [x] CI verde no GitHub (ruff + pytest)

**Saída:** `make test` passa no GitHub Actions **e** dentro do container `lab` na VPS (27 passed).

## Fase 1 — Dados ✅ concluída em 30/10/2026

Objetivo: descobrir quanto histórico M1 de WIN/WDO é acessível de graça, com qualidade medida.

Guia: [mt5.md](mt5.md). Ambiente: **Mac + VPS Linux** (sem computador Windows). Decisão de
28/10/2026: só MT5 demo nesta fase, **na VPS**; Profit Pro adiado sem previsão. Depende da Fase 0.

- [x] Ativar MT5 demo da Clear — contratado em 27/10/2026: painel mostra **Grátis**, conta netting
- [x] Subir MT5 na VPS (`docker compose --profile mt5 up -d mt5`, imagem `lprett/mt5linux`) — 28/10
- [x] Fixar o digest da imagem em `MT5_IMAGE` e registrar no Notion — 29/10
- [x] Abrir a tela pelo túnel (http://localhost:8080) e logar no simulador (`ClearInvestimentos-DEMO`)
- [x] "Máx. barras no gráfico" = Ilimitado e reexportar — 29/10: **mesmo resultado** (~100 mil barras
      desde 02/2026); o limite é do servidor demo da Clear, não do terminal
- [x] Exportar M5 do WIN desde 2010 — 30/10: **exatamente 100.000 barras**, de 30/03/2023 a 29/10/2026
      (895 pregões)
- [x] Exportar M15 do WIN desde 2010 — 30/10: 46.662 barras, de **29/10/2021** a 29/10/2026 (1.248
      pregões). Dois limites no servidor demo: **100 mil barras** por tempo gráfico (corta M1 e M5) e
      **~5 anos de retenção**, em janela móvel (corta M15)
- [x] Exportar M5 e M15 do WDO — 30/10: M15 trouxe 46.666 barras (1.248 pregões, de 29/10/2021 a 29/10/2026,
      0 lacunas intradiárias); M5 trouxe 100.000 barras (887 pregões, de 12/04/2023 a 29/10/2026)
- [x] Validação cruzada: M5 e M15 do MT5 = reamostragem do nosso M1 (WIN: 20.024 M5 e 6.734 M15; WDO: 19.970 M5
      e 6.658 M15; OHLC, tick volume e real volume idênticos com diferença 0,000000)
- [x] Levantar rolagens do período longo (`robob3 rolagens-candidatas`, M15 de 5 anos) e completar
      `config/rolagens.yaml`: WIN 30/30 confirmadas; WDO 39/59 confirmadas + 17 pendentes com salto ≥ 0
      incluídas pela regra (nenhuma troca observada fora dela); 3 pendentes sem ajuste (29/09/2023,
      31/10/2023, 30/08/2024)
- [ ] Arquivar exportações periódicas: a janela de 5 anos e a de 100 mil barras M1 andam todo dia;
      o que sair dela não volta (até o gravador da Fase 4 existir)
- [x] Confirmar negociação algorítmica desligada no terminal MT5; `config/risk.yaml` restrito a `modo: demo`
- [x] Confirmar `healthy` em `docker compose ps` (healthcheck revisado: lê `/proc/net/tcp`)
- [x] Identificar símbolos contínuos (`WIN$N`, `WDO$N`)
- [x] Rolagem do `WIN$N` (30/10, `robob3 gaps`): troca no dia do vencimento (quarta mais próxima do
      dia 15 dos meses pares), **sem ajuste** — saltos de ~+2% em 18/02, 15/04, 17/06, 12/08, 14/10
- [x] Rolagem do `WDO$N`: troca no **último dia útil do mês**, sem ajuste (~+0,6% a +0,9%) em 7 de 8
      meses; **março pendente** (sem salto em 31/03)
- [x] Datas de troca em `config/rolagens.yaml` e `robob3 ajustar-rolagem` (aditivo ou razão)
- [x] Exportar M1 desde 10/2018 à mão (Símbolos > Barras) para `C:\export` (= `data/raw/`);
      1ª extração: ~100 mil barras, 177–180 pregões (02/2026 → 29/10/2026) — ver Notion, seção 4.1
- [x] `robob3 relatorio-dados` em cada arquivo; registrar no Notion: servidor, símbolo, datas efetivas,
      nº de barras, lacunas, duplicados, SHA-256 do arquivo, data da extração
- [x] Conferir horários: Quarta-feira de Cinzas abre às 13:00 (2022, 2024, 2025, 2026); pregões até
      03/11/2023 encerravam às 18:00 (última barra M15 às 17:45); pausas pós-eleição (05/10 e 26/10)
- [ ] Conferência com fonte **independente** (a validação cruzada M5/M15 × M1 usa a mesma fonte, a
      Clear): negócios da amostra Nelogica de WDO em 02/03/2022 13:00:41–13:00:48 devem cair dentro da
      máxima/mínima da barra M15 de 13:00 do `WDO$N` nesse dia (se a série era o mesmo contrato)
- [x] Gerar M5/M15 a partir de M1 (`robob3 reamostrar`) — sem preencher lacunas (Parquet salvo em `data/processed/`)
- [x] Remover pregões parciais das pontas (`robob3 remover-incompletos` ou `reamostrar --remover-incompletos`)
      preservando pregões internos legítimos

**Saída:** tabela no Notion com cobertura real por ativo e decisão **"o período disponível basta para
iniciar o backtest"**. Critério atingido: 5 anos completos de dados intradiários M15 (1.248 pregões) e
mais de 3,5 anos em M5 de qualidade institucional (zero OHLC inconsistente, zero duplicados, zero volume
zero, zero lacunas internas no WDO M15) cobrem diversos regimes macroeconômicos (alta/baixa de juros,
eleições, choques de volatilidade). O período disponível é mais que suficiente para especificar a
estratégia (Fase 2) e rodar o backtest e validação temporal (Fase 3).

## Fase 2 — Especificação da estratégia (atual)

- [ ] Escrever a primeira estratégia em `docs/estrategias/` a partir do `TEMPLATE.md` — **um ativo**
- [ ] Regras completas: entrada, saída, stop, alvo, horário, tamanho, limite diário, custo por operação
- [ ] Definir hipótese conservadora para barra M1 que toca stop e alvo juntos
- [ ] Separar períodos: desenvolvimento × fora da amostra (definidos **antes** de testar)

**Saída:** documento revisado; qualquer pessoa conseguiria reproduzir os sinais à mão.

## Fase 3 — Backtest em Python

- [ ] Motor de backtest barra a barra com custos, spread e derrapagem configuráveis
- [ ] Tratamento de rolagem (comparar série ajustada × não ajustada)
- [ ] Métricas: resultado líquido, drawdown máximo, expectativa por operação, frequência, por ano/regime
- [ ] Validação temporal progressiva (walk-forward)
- [ ] Comparar: base × base + filtro de calendário (notícias/IA só com dados históricos adequados)

**Saída:** resultado líquido robusto fora da amostra — ou revisão/abandono da hipótese.

## Fase 4 — MT5 demo na VPS + gravador de dados próprio

Sem computador Windows, a VPS é o **único** lugar onde o MT5 fica ligado e conversa com Python.
O container do MT5 já sobe na Fase 1; aqui entra a ponte.

- [ ] Cliente `mt5linux==1.1.1` (mesmo autor da imagem) num serviço na rede `trading` → `mt5:18812`
- [ ] Adaptar `scripts/mt5_exportar.py` para o cliente `mt5linux`
- [ ] Validar ponte Python ↔ MT5 (mt5linux/RPyC): `account_info`, `symbol_info`, `copy_rates_range`
- [ ] Testar estabilidade: reinício do container, queda de rede, reconexão
- [ ] Gravador **separado da execução**: M1 + ticks (se autorizados), com metadados de coleta, em Parquet
- [ ] Verificação diária de lacunas e backup fora da VPS

**Saída:** 10 pregões seguidos gravando sem lacuna não explicada.

## Fase 5 — Execução simulada (2–3 meses)

- [ ] Estratégia rodando no MT5 demo com limites rígidos (`config/risk.yaml`)
- [ ] Logs JSON + SQLite, alertas Telegram, disjuntor de perda diária, `/panico`
- [ ] Reconciliação de posições ao reiniciar
- [ ] Testes de falha forçada (rede, reinício, MT5 fora)
- [ ] Ponte de sinais: IA só `DESARMAR`/`REDUZIR` (validador em `src/robob3/signals.py`)
- [ ] Relatório mensal: demo × operações manuais reais separadas, custos, falhas, mudanças

**Saída:** ≥ 30 pregões em demo — verificação operacional, **não** prova de lucratividade.

## Fase 6 — Revisão e decisão

- [ ] Revisar desempenho líquido, riscos, custos e falhas
- [ ] Decisão documentada no Notion sobre próximos passos (operação real automatizada exige decisão
      explícita e nova revisão de código — o modo `real` não existe neste código hoje)
