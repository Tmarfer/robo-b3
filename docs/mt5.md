# MT5 — conta demo da Clear na VPS e exportação de histórico

**Conta:** MetaTrader 5 (Simulador) contratado em 27/10/2026. Painel da Clear: custo mensal
**Grátis**, conta **netting** (uma posição líquida por ativo, como na B3).
"Resetar limite" no painel volta o saldo simulado ao inicial.

**Ambiente:** Mac (M4 Pro) + VPS Linux Hostinger. Sem computador Windows. Decisão de 28/10/2026:
concentrar o MT5 **na VPS**, dentro de Docker/Wine, com a tela aberta no **navegador do Mac** por
túnel SSH.

| Fase | O que usa do MT5 na VPS |
| --- | --- |
| 1 — dados (agora) | Tela no navegador: login, símbolos, **exportação manual** das barras M1 |
| 4 — ponte | Python ↔ MT5 por `mt5linux` (RPyC, porta 18812, só rede interna) |
| 5 — simulação | Execução em demo pela ponte, com os limites de `config/risk.yaml` |

Pré-requisito: Fase 0 (bootstrap, Docker e clone na VPS — `docs/vps-setup.md`).

## Imagem

`lprett/mt5linux` — mantida pelo autor do pacote `mt5linux` (github.com/lucas-campagna/mt5linux,
pasta `docker/`). Alpine + Wine + MT5 em modo *portable* em `C:\MT5`, tela via noVNC, servidor RPyC
e um *watchdog* que reinicia o terminal se ele travar. Na 1ª execução vem com negociação
algorítmica **desligada** e "Máx. barras" = 1.000.000.

Por que não `gmag11/metatrader5_vnc` (a do rascunho no Notion): sem atualização desde 12/2025 e o
script de partida instala `mt5linux>=0.1.9` sem fixar versão — hoje isso puxa a 1.x reescrita, cujo
servidor não aceita mais os parâmetros que a imagem usa. A ponte Python ali provavelmente quebrou.

Riscos da escolhida: projeto jovem e com mudanças frequentes. Por isso **fixar o digest** depois do
primeiro teste e só atualizar fora do pregão. Não há suporte da Clear nem da MetaQuotes para Wine.

### Problemas encontrados na VPS (30/10/2026)

- **Conta apagada ao recriar o container.** Log do terminal: `Accounts: deleted due security reason`.
  O MT5 amarra `Config/accounts.dat` à identidade da máquina, e cada recriação trazia um hostname
  novo. Corrigido com `hostname: mt5` no compose. Para não depender da tela, preencher
  `MT5_LOGIN`, `MT5_PASSWORD` e `MT5_SERVER` (conta **demo**) no `.env`, que não vai para o git.
- **`mt5.initialize()` → `(-10005, 'IPC timeout')`.** O terminal atualizou sozinho para o build
  6092 e avisa `unstable and unsupported Wine 9.0 ... please upgrade to Wine 10.0 or later`; a
  imagem `lprett/mt5linux` usa Wine 9.0. Hipótese do Antigravity: nesse build o pipe IPC usado pelo
  pacote `MetaTrader5` não abre em Wine < 10. A confirmar depois de a conta estar logada (sem conta
  o terminal também pode não responder). **Feito:** imagem própria `infra/mt5/Dockerfile` (base
  `lprett/mt5linux` fixada por digest, Alpine 3.20, com o Wine do Alpine edge). Em 30/10 o terminal
  subiu em `Wine 11.0` sem o aviso. A ponte ainda não foi validada: falta a conta demo logada.
- **Loop de reinício com o Wine 11** (achado pelo Codex em 30/10, 187 reinícios). No reinício, a
  função `apply_mt5_config` da imagem devolve 1 quando não é a primeira execução, e o `set -e` do
  script principal encerra o container antes do MT5. Além disso, o Wine 11 rejeita
  `wineboot -init` (o certo é `-i`) e precisa de GnuTLS. Os três ajustes estão no
  `infra/mt5/Dockerfile`, com `grep -q` para o build falhar se a imagem base mudar. Wine instalado:
  `11.0-r0` (Alpine edge, 30/10/2026).
- **Primeira partida de um container novo:** o script da imagem extrai o pacote do terminal em
  `mt5-data/` e grava `mt5-data/common.ini` a partir do `.env`, com a senha em texto puro. É o
  login automático previsto (conta demo). `mt5-data/` está fora do git; ao montar o backup fora da
  VPS, tratar essa pasta como sensível.
- **Não** alterar nem desmontar o `terminal64.exe` e não usar chaves não documentadas no
  `common.ini`: além de frágil a cada atualização, sai do uso permitido do terminal.
- O healthcheck procurava a porta errada (`0x4974` = 18804); o certo é `0x497C` = 18812.
  `tests/test_compose.py` confere a conta.

## 1. Subir

Na VPS, em `~/robo-b3`:

```bash
nano .env                     # defina MT5_UI_PASSWORD (senha da tela)
mkdir -p mt5-data data/raw
docker compose --profile mt5 up -d mt5
docker compose logs -f mt5    # esperar "All services started" (1ª vez leva alguns minutos)
```

## 2. Abrir a tela no Mac

Com o `~/.ssh/config` do `docs/vps-setup.md` (túneis 8080 e 5901):

```bash
ssh robo-b3
```

Deixe essa sessão aberta e acesse **http://localhost:8080** no navegador do Mac → Connect →
senha `MT5_UI_PASSWORD`.

## 3. Entrar na conta demo

Arquivo → Abrir conta → digite o nome do **servidor do simulador da Clear** (enviado pela Clear) →
"Conectar com conta existente" → login e senha → **salvar senha**. Confirme a conexão no canto
inferior direito. Anote no Notion: nome exato do servidor e build (Ajuda → Sobre).

Se o servidor não aparecer na busca, peça à Clear o endereço do servidor demo (`IP:porta`).

## 4. Ajustes

- Ferramentas → Opções → Gráficos → **Máx. barras no gráfico: Ilimitado** → reiniciar o terminal
  (`docker compose restart mt5`).
- Ferramentas → Opções → Expert Advisors → "Permitir algoritmo de negociação" **desligado**.

## 5. Símbolos e exportação M1

1. Exibir → Símbolos → pesquisar `WIN` e `WDO`. Candidatos: `WIN$N`, `WDO$N` (ou `WIN$`, `WIN@`).
   Anote **descrição** e **caminho**; pergunte à Clear a regra de rolagem.
2. Aba **Barras** → símbolo, período **M1**, de **01/10/2018** até hoje → **Solicitar** → esperar.
3. **Exportar barras** → salvar em **`C:\export\`** com o nome `WIN-N_M1_clear-mt5_AAAAMMDD.csv`.
   `C:\export` é a pasta `data/raw/` da VPS.
4. Repetir para `WDO$N`. A data pedida não garante a recebida: anote a primeira linha que veio.
   Se vier curto, Solicitar de novo ou abrir um gráfico M1 e rolar para trás.

## 6. Relatório de qualidade

```bash
sudo chown -R "$USER" data/raw   # arquivos gravados pelo container saem como root
make docker-build                 # primeira vez
docker compose run --rm lab relatorio-dados data/raw/WIN-N_M1_clear-mt5_AAAAMMDD.csv
```

O relatório mostra a abertura/fechamento típicos e lista os **pregões incompletos**, em dois tipos:

- **ponta** — 1º ou último dia do arquivo (corte do limite de barras, exportação durante o
  pregão). Removidos por padrão.
- **interno: investigar** — dia no meio do período. Pode ser pregão oficial com horário especial
  (ex.: Quarta-feira de Cinzas abre às 13:00 — dia real de negociação, não remover) ou problema
  nos dados. Só remover com `--remover-internos`, depois de investigar e registrar no Notion.

**Rolagem:** as séries `WIN$N` e `WDO$N` da Clear não são ajustadas. As datas de troca
identificadas ficam em `config/rolagens.yaml` (versionado). Para indicadores que atravessam dias:

```bash
docker compose run --rm lab ajustar-rolagem data/raw/WIN-N_M1_clear-mt5_20261029.csv --ativo WIN \
  --saida data/processed/WIN-N_M1_clear-mt5_20261029_ajustado.csv
```

Para séries longas (M5/M15 de anos), levantar as datas pela regra de cada contrato e conferir:

```bash
docker compose run --rm lab rolagens-candidatas data/raw/WIN-N_M15_clear-mt5_AAAAMMDD.csv --regra win
docker compose run --rm lab rolagens-candidatas data/raw/WDO-N_M15_clear-mt5_AAAAMMDD.csv --regra wdo
```

"Confirmada" = salto positivo e o maior entre o dia e seus vizinhos; "pendente" = revisar à mão
(ex.: março/2026 do WDO). O comando imprime as listas no formato do YAML, mas **não grava**:
revisar antes de copiar.

O método aditivo (padrão) mantém as diferenças em pontos dentro de cada dia. Preços de execução no
backtest continuam vindo da série original. A cada nova extração, conferir novas trocas com
`robob3 gaps` e atualizar o YAML.

Para ver dia a dia: `robob3 pregoes ARQUIVO`. Para os maiores saltos entre o fechamento de um dia e
a abertura do seguinte (rolagem da série `$N`, eventos): `robob3 gaps ARQUIVO --top 15`. Antes do backtest, descartar as pontas:

```bash
docker compose run --rm lab remover-incompletos data/raw/WIN-N_M1_clear-mt5_AAAAMMDD.csv \
  --saida data/processed/WIN-N_M1_clear-mt5_AAAAMMDD_completos.csv
docker compose run --rm lab reamostrar data/raw/WIN-N_M1_clear-mt5_AAAAMMDD.csv --minutos 5 \
  --remover-incompletos --saida data/processed/WIN-N_M5_clear-mt5_AAAAMMDD.parquet
```

Lacunas **no meio** do dia (leilão, pausa — ex.: 26/10/2026 09:27–09:42) não removem o pregão:
são eventos de mercado e continuam no relatório de lacunas. Se a B3 mudar o horário no período
(ex.: horário de verão nos EUA), informar `--abertura`/`--fechamento`.

Registrar no Notion, seção 4.1, por ativo: servidor, símbolo, primeira/última barra, pregões,
pregões incompletos, lacunas, duplicados, SHA-256 e data da extração.

## 7. Fixar a versão da imagem

Depois que login e exportação funcionarem:

```bash
docker inspect --format '{{index .RepoDigests 0}}' lprett/mt5linux:latest
# colar o resultado (lprett/mt5linux@sha256:...) em MT5_IMAGE no .env e registrar no Notion
```

## Alternativa rápida: MT5 para macOS

Para só olhar a conta ou comparar algo antes da VPS estar pronta: baixar o MT5 para macOS no site
da MetaQuotes (é o terminal Windows empacotado com Wine; no chip Apple roda via Rosetta), entrar no
servidor do simulador e usar os mesmos passos 4 e 5, salvando em `~/Downloads`. Depois
`scp ~/Downloads/W*-N_M1_*.csv robo-b3:~/robo-b3/data/raw/`.

## Ponte Python (Fase 4)

- Cliente: `mt5linux==1.1.1` (fixar junto com o digest da imagem), conectando em `mt5:18812` pela
  rede `trading` — **não** usar o modo em que a biblioteca cria containers sozinha.
- `scripts/mt5_exportar.py` usa o pacote `MetaTrader5` (só Windows). Na Fase 4 ele será adaptado
  para o cliente `mt5linux`, que expõe a mesma API.

## Cuidados

- Horários são os do **servidor** da corretora; confirmar o fuso com um candle conhecido.
- `<VOL>` = volume real (contratos); `<TICKVOL>` = número de negócios/ticks.
- Lacunas não são corrigidas, só identificadas.
- Se a VPS reiniciar, o container volta sozinho (`restart: unless-stopped`); o histórico em
  `mt5-data/` persiste. Na recriação do container a imagem reaplica a configuração inicial —
  conferir login e "Máx. barras".
