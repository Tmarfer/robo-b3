# MT5 — conta demo da Clear e exportação de histórico

**Conta:** MetaTrader 5 (Simulador) contratado em 27/10/2026. Painel da Clear: custo mensal
**Grátis**, conta **netting** (uma posição líquida por ativo, como na B3).
"Resetar limite" no painel volta o saldo simulado ao inicial.

**Ambiente:** não há computador Windows no projeto — só **Mac** e a **VPS Linux**.

| Onde | Para quê | Fase |
| --- | --- | --- |
| MT5 no Mac | Conferir a conta, símbolos e exportar o histórico M1 **à mão** | 1 (agora) |
| MT5 na VPS (Docker/Wine), tela via navegador do Mac | Terminal sempre ligado; ponte com Python; gravador de dados; execução simulada | 4 |

O pacote Python `MetaTrader5` só existe para Windows. No Mac ele não roda; na VPS ele roda
**dentro do Wine**, junto com o terminal. Por isso a exportação da Fase 1 é manual.

## 1. Instalar no Mac e entrar

1. Baixe o **MetaTrader 5 para macOS** no site da MetaQuotes (metatrader5.com → Download → macOS).
   É o terminal Windows empacotado com Wine; em Macs com chip Apple roda via Rosetta.
   O botão "Baixar MT5" do painel da Clear provavelmente entrega o instalador Windows (`.exe`).
2. Arquivo → Abrir conta → digite o nome do **servidor do simulador da Clear** (enviado pela Clear
   por e-mail ou no painel) → "Conectar com conta existente" → login e senha → salvar senha.
3. Confirme no canto inferior direito que conectou (barra com a latência).
4. Anote no Notion: nome exato do servidor e build do terminal (Ajuda → Sobre).

Se o servidor da Clear não aparecer no app do Mac, peça à Clear o endereço do servidor demo
(`IP:porta`) ou passe direto para o MT5 na VPS (Fase 4, `docker compose --profile mt5`).

## 2. Ajustes antes de puxar histórico

- Ferramentas → Opções → Gráficos → **Máx. barras no gráfico: Ilimitado** → OK → reiniciar o MT5.
  Sem isso o terminal corta o histórico.
- Ferramentas → Opções → Expert Advisors → "Permitir algoritmo de negociação" **desligado**.
  Nesta fase só lemos dados.

## 3. Achar os símbolos contínuos

Exibir → Símbolos (⌘U / Ctrl+U) → pesquisar `WIN` e `WDO`. Candidatos: `WIN$N`, `WDO$N`
(e variações como `WIN$`, `WIN@`). Para cada um anote **descrição** e **caminho**, e pergunte à
Clear qual a regra de rolagem (quando troca de vencimento e se há ajuste de preço).

## 4. Exportar M1

Símbolos → aba **Barras** → símbolo `WIN$N`, período **M1**, de **01/10/2018** até hoje →
**Solicitar** → esperar terminar → **Exportar barras** → salvar como
`WIN-N_M1_clear-mt5_AAAAMMDD.csv`. Repetir para `WDO$N`.

A data pedida não garante a recebida: anote a **primeira linha** que veio. Se vier curto, clique
em Solicitar de novo (o terminal baixa do servidor aos poucos) ou abra um gráfico M1 do símbolo e
role para trás.

## 5. Relatório de qualidade e envio para a VPS

No Mac (Terminal), com Python 3.11+:

```bash
git clone git@github.com:Tmarfer/robo-b3.git && cd robo-b3
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
robob3 relatorio-dados ~/Downloads/WIN-N_M1_clear-mt5_*.csv
```

Enviar para a VPS (depois do bootstrap):

```bash
scp ~/Downloads/W*-N_M1_clear-mt5_*.csv robo-b3:~/robo-b3/data/raw/
```

Registrar no Notion, seção 4.1, por ativo: servidor, símbolo, primeira/última barra, pregões,
lacunas, duplicados, SHA-256 e data da extração. Esse é o critério de saída da Fase 1.

## Script `scripts/mt5_exportar.py`

Faz o mesmo que o passo 4 de forma reprodutível e grava um manifesto JSON, mas precisa do pacote
`MetaTrader5`, ou seja, de um Python Windows: o Python dentro do Wine na VPS (Fase 4) ou uma VM
Windows. Fica pronto para quando esse ambiente existir.

## Cuidados

- Os horários são os do **servidor** da corretora. Confirmar o fuso comparando um candle conhecido
  (ex.: abertura das 9:00) com outra fonte.
- `<VOL>` é o volume real (contratos); `<TICKVOL>` é o número de negócios/ticks.
- Lacunas não são corrigidas, só identificadas.
- `mt5linux` (ponte Python Linux ↔ MT5 no Wine): a versão 1.x no PyPI (jul–ago/2026) foi reescrita
  pelo mesmo autor, cria o próprio container (`lprett/mt5linux`) e mudou a API. Não combina com a
  imagem `gmag11/metatrader5_vnc` usada no rascunho do Notion. Escolher **uma** das duas na Fase 4 e
  fixar versões.
