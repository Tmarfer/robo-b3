# MT5 no Windows — conta demo da Clear e exportação de histórico

Primeiro uso do MT5 no projeto (Fase 1). Roda no seu computador Windows e **não depende da VPS**.
O MT5 na VPS (Docker/Wine) fica para a Fase 4.

**Conta:** MetaTrader 5 (Simulador) contratado em 27/10/2026. Painel da Clear: custo mensal
**Grátis**, conta **netting** (uma posição líquida por ativo, como na B3).
"Resetar limite" no painel volta o saldo simulado ao inicial.

## 1. Instalar e entrar

1. Painel da Clear → Contratos ativos → **Baixar MT5** e instalar.
2. Arquivo → Abrir conta / Conectar a conta: use o **servidor e o login do simulador** que a Clear
   enviou por e-mail/painel. Marque "salvar senha".
3. Confirme no canto inferior direito que conectou (barra verde com a latência).
4. Anotar no Notion: nome exato do servidor, build do terminal (Ajuda → Sobre).

## 2. Ajustes antes de puxar histórico

- Ferramentas → Opções → Gráficos → **Máx. barras no gráfico: Ilimitado** → OK → reiniciar o MT5.
  Sem isso o terminal corta o histórico (o script avisa se o limite estiver baixo).
- Ferramentas → Opções → Expert Advisors → "Permitir algoritmo de negociação" **desligado** por
  enquanto. Nesta fase só lemos dados.

## 3. Achar os símbolos contínuos

Exibir → Símbolos (Ctrl+U) → pesquisar `WIN` e `WDO`. Candidatos: `WIN$N`, `WDO$N`
(e variações como `WIN$`, `WIN@`). Para cada um, anotar **descrição** e **caminho**, e perguntar à
Clear qual a regra de rolagem (quando troca de vencimento e se há ajuste de preço).

## 4a. Exportar à mão (rápido, para ver o que existe)

Símbolos → aba **Barras** → símbolo `WIN$N`, período **M1**, de **01/10/2018** até hoje →
**Solicitar** → **Exportar barras**. Repetir para `WDO$N`. A data pedida não garante a recebida:
ver a primeira linha da tabela.

## 4b. Exportar pelo script (reprodutível, gera manifesto)

Uma vez, num PowerShell, com Python 3.12 instalado (python.org, marcar "Add to PATH"):

```powershell
git clone git@github.com:Tmarfer/robo-b3.git
cd robo-b3
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,mt5]"
```

Com o MT5 **aberto e logado**:

```powershell
python scripts/mt5_exportar.py --listar WIN
python scripts/mt5_exportar.py --simbolo 'WIN$N' --tf M1 --inicio 2018-10-01
python scripts/mt5_exportar.py --simbolo 'WDO$N' --tf M1 --inicio 2018-10-01
```

> No PowerShell use **aspas simples** em `'WIN$N'`; sem elas `$N` vira variável vazia e o
> símbolo vira `WIN`.

O script baixa mês a mês e grava em `data/raw/`:
- `WIN-N_M1_mt5_AAAAMMDD.csv` — mesmo formato do export manual
- `WIN-N_M1_mt5_AAAAMMDD.json` — manifesto: servidor, símbolo, datas pedidas × recebidas,
  meses sem dados, conta demo/netting, build, limite de barras e relatório de qualidade

Se a primeira execução vier curta, rode de novo: o terminal às vezes baixa o histórico do servidor
aos poucos. Abrir um gráfico M1 do símbolo e rolar para trás também força o download.

## 5. Levar para a VPS e registrar

```powershell
scp data/raw/WIN-N_M1_mt5_*.* robo-b3:~/robo-b3/data/raw/
```

(ou rodar `robob3 relatorio-dados data/raw/ARQUIVO.csv` no próprio Windows)

Registrar no Notion, seção 4.1, por ativo: servidor, símbolo, primeira/última barra, pregões,
lacunas, meses sem dados, SHA-256 e data da extração. Esse é o critério de saída da Fase 1.

## Cuidados

- Os horários são os do **servidor** da corretora. Confirmar o fuso comparando um candle conhecido
  (ex.: abertura das 9:00) com o Profit, quando ele estiver ativo.
- Volume: `<VOL>` é o volume real (contratos); `<TICKVOL>` é o número de negócios/ticks.
- Lacunas não são corrigidas: só identificadas.
