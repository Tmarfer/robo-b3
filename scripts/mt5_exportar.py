"""Exporta barras do MT5 para data/raw/ no mesmo formato do export manual + manifesto JSON.

Roda no WINDOWS, com o terminal MT5 aberto e logado na conta demo (só leitura: não envia ordens).

    pip install -e ".[mt5]"
    python scripts/mt5_exportar.py --listar WIN
    python scripts/mt5_exportar.py --simbolo 'WIN$N' --tf M1 --inicio 2018-10-01

No PowerShell use aspas SIMPLES em 'WIN$N' (sem elas, $N vira variável vazia).

Antes: no MT5, Ferramentas > Opções > Gráficos > "Máx. barras no gráfico" = Ilimitado.
Ver docs/mt5-windows.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from robob3.data import avaliar_barras, escrever_barras_mt5
from robob3.data.mt5_csv import rates_para_df

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "H1": mt5.TIMEFRAME_H1,
    "D1": mt5.TIMEFRAME_D1,
}
MINUTOS = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "D1": 1440}


def conectar(caminho_terminal: str | None) -> None:
    ok = mt5.initialize(path=caminho_terminal) if caminho_terminal else mt5.initialize()
    if not ok:
        sys.exit(f"Falha ao conectar no MT5: {mt5.last_error()} — o terminal está aberto e logado?")


def listar(filtro: str) -> None:
    for s in mt5.symbols_get(f"*{filtro}*") or []:
        print(f"{s.name:<14} {s.path:<40} {s.description}")


def meses(inicio: datetime, fim: datetime):
    a = inicio
    while a < fim:
        b = min((a + pd.offsets.MonthBegin(1)).to_pydatetime(), fim)
        yield a, b
        a = b


def baixar(
    simbolo: str, tf: str, inicio: datetime, fim: datetime
) -> tuple[pd.DataFrame, list[str]]:
    partes, vazios = [], []
    for a, b in meses(inicio, fim):
        rates = None
        for _ in range(3):  # o terminal pode precisar de alguns segundos para baixar o histórico
            rates = mt5.copy_rates_range(simbolo, TIMEFRAMES[tf], a, b)
            if rates is not None and len(rates):
                break
            time.sleep(1.5)
        n = 0 if rates is None else len(rates)
        print(f"  {a:%Y-%m}: {n} barras" + ("" if rates is not None else f" {mt5.last_error()}"))
        if n:
            partes.append(rates_para_df(rates))
        else:
            vazios.append(f"{a:%Y-%m}")
    if not partes:
        return pd.DataFrame(), vazios
    df = pd.concat(partes)
    # janelas mensais se tocam nas bordas: só remove repetição entre blocos
    return df[~df.index.duplicated(keep="first")].sort_index(), vazios


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--listar", metavar="FILTRO", help="lista símbolos que contêm FILTRO")
    p.add_argument("--simbolo")
    p.add_argument("--tf", default="M1", choices=TIMEFRAMES)
    p.add_argument("--inicio", default="2018-10-01")
    p.add_argument("--fim", default=None, help="padrão: agora")
    p.add_argument("--saida", default="data/raw")
    p.add_argument("--terminal", default=None, help="caminho do terminal64.exe, se houver vários")
    args = p.parse_args()

    conectar(args.terminal)
    try:
        if args.listar:
            listar(args.listar)
            return 0
        if not args.simbolo:
            p.error("informe --simbolo ou --listar")

        if not mt5.symbol_select(args.simbolo, True):
            sys.exit(f"Símbolo {args.simbolo} não encontrado. Use --listar.")
        info = mt5.symbol_info(args.simbolo)
        conta = mt5.account_info()
        terminal = mt5.terminal_info()

        inicio = datetime.fromisoformat(args.inicio).replace(tzinfo=UTC)
        fim = datetime.now(UTC)
        if args.fim:
            fim = datetime.fromisoformat(args.fim).replace(tzinfo=UTC)
        print(f"{args.simbolo} {args.tf} de {inicio:%Y-%m-%d} a {fim:%Y-%m-%d} — {conta.server}")
        df, vazios = baixar(args.simbolo, args.tf, inicio, fim)
        if df.empty:
            sys.exit("Nenhuma barra recebida. Abra um gráfico do símbolo e tente de novo.")

        extracao = datetime.now(UTC)
        nome = re.sub(r"[^A-Za-z0-9]+", "-", args.simbolo).strip("-")
        csv = Path(args.saida) / f"{nome}_{args.tf}_mt5_{extracao:%Y%m%d}.csv"
        escrever_barras_mt5(df, csv)

        rel = avaliar_barras(df, minutos=MINUTOS[args.tf])
        manifesto = {
            "arquivo": csv.name,
            "simbolo": args.simbolo,
            "descricao": info.description,
            "caminho_simbolo": info.path,
            "timeframe": args.tf,
            "pedido": {"inicio": args.inicio, "fim": args.fim or f"{fim:%Y-%m-%d}"},
            "recebido": {"primeira": rel.primeira, "ultima": rel.ultima, "barras": rel.linhas},
            # meses antes da 1ª barra são esperados; no meio do período, investigar
            "meses_sem_dados": vazios,
            "servidor": conta.server,
            "corretora": conta.company,
            "conta_demo": conta.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO,
            "netting": conta.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING,
            "terminal_build": terminal.build,
            "max_barras_grafico": terminal.maxbars,
            "extraido_em_utc": extracao.isoformat(timespec="seconds"),
            "horario": "servidor da corretora, sem fuso — confirmar",
            "qualidade": rel.to_dict(),
        }
        csv.with_suffix(".json").write_text(
            json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nOK: {csv} ({rel.linhas} barras, {rel.primeira} -> {rel.ultima})")
        print(f"Lacunas intradiárias: {rel.lacunas_intradiarias}; pregões: {rel.pregoes}")
        if terminal.maxbars < 10_000_000:
            aviso = f"'Máx. barras no gráfico' = {terminal.maxbars}"
            print(f"Aviso: {aviso}; pode limitar o histórico.")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    sys.exit(main())
