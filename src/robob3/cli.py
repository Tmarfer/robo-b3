"""Linha de comando: `robob3 <comando> ...`."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import time
from pathlib import Path

from robob3.config import carregar_config
from robob3.data import (
    avaliar_barras,
    escrever_barras_mt5,
    gaps_abertura,
    ler_barras_mt5,
    reamostrar,
    remover_pregoes_incompletos,
    resumo_pregoes,
)


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _horario(texto: str) -> time:
    return time.fromisoformat(texto)


def _opcoes_pregao(args: argparse.Namespace) -> dict:
    return {
        "abertura": args.abertura,
        "fechamento": args.fechamento,
        "tolerancia_min": args.tolerancia,
    }


def _remover_incompletos(df, args: argparse.Namespace):
    limpo, removidos = remover_pregoes_incompletos(
        df, internos=args.remover_internos, **_opcoes_pregao(args)
    )
    for p in removidos:
        tipo = "ponta" if p.ponta else "interno"
        print(f"removido [{tipo}] {p.data} {p.primeira}-{p.ultima} ({p.barras} barras): {p.motivo}")
    return limpo


def _gravar(df, saida: Path, formato_mt5: bool) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    if saida.suffix == ".parquet":
        df.to_parquet(saida)
    elif formato_mt5:
        escrever_barras_mt5(df, saida)
    else:
        df.to_csv(saida)


def cmd_relatorio(args: argparse.Namespace) -> int:
    caminho = Path(args.arquivo)
    df = ler_barras_mt5(caminho)
    rel = avaliar_barras(df, minutos=args.minutos, **_opcoes_pregao(args))
    meta = {"arquivo": caminho.name, "sha256": _sha256(caminho)}
    if args.json:
        print(json.dumps(meta | rel.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("\n".join(f"{k}: {v}" for k, v in meta.items()))
        print(rel.to_texto())
    return 0


def cmd_pregoes(args: argparse.Namespace) -> int:
    resumo = resumo_pregoes(ler_barras_mt5(args.arquivo))
    print("data,primeira,ultima,barras")
    for dia, r in resumo.iterrows():
        print(f"{dia:%Y-%m-%d},{r.primeira:%H:%M},{r.ultima:%H:%M},{r.barras}")
    return 0


def cmd_gaps(args: argparse.Namespace) -> int:
    gaps = gaps_abertura(ler_barras_mt5(args.arquivo)).head(args.top)
    print("data,dia_semana,fech_anterior,abertura,gap_pts,gap_pct")
    for dia, r in gaps.iterrows():
        print(
            f"{dia:%Y-%m-%d},{dia:%a},{r.fech_anterior:g},{r.abertura:g},"
            f"{r.gap_pts:+g},{r.gap_pct:+.2f}"
        )
    return 0


def cmd_remover_incompletos(args: argparse.Namespace) -> int:
    df = ler_barras_mt5(args.arquivo)
    limpo = _remover_incompletos(df, args)
    saida = Path(args.saida)
    _gravar(limpo, saida, formato_mt5=True)
    print(f"{len(df)} -> {len(limpo)} barras: {saida}")
    return 0


def cmd_reamostrar(args: argparse.Namespace) -> int:
    df = ler_barras_mt5(args.arquivo)
    if args.remover_incompletos:
        df = _remover_incompletos(df, args)
    out = reamostrar(df, args.minutos)
    saida = Path(args.saida)
    _gravar(out, saida, formato_mt5=False)
    print(f"{len(df)} barras -> {len(out)} barras M{args.minutos}: {saida}")
    return 0


def cmd_validar_config(args: argparse.Namespace) -> int:
    cfg = carregar_config(args.arquivo)
    print(json.dumps(cfg.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


_AJUDA_INTERNOS = (
    "remover também pregões incompletos no meio do período (horário especial ou problema) — "
    "só depois de investigá-los"
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="robob3")
    sub = p.add_subparsers(dest="comando", required=True)

    pregao = argparse.ArgumentParser(add_help=False)
    pregao.add_argument("--abertura", type=_horario, help="HH:MM (padrão: mais frequente)")
    pregao.add_argument("--fechamento", type=_horario, help="HH:MM da última barra esperada")
    pregao.add_argument("--tolerancia", type=int, default=5, help="minutos (padrão 5)")

    r = sub.add_parser(
        "relatorio-dados", parents=[pregao], help="qualidade de um CSV de barras do MT5"
    )
    r.add_argument("arquivo")
    r.add_argument("--minutos", type=int, default=1, help="timeframe do arquivo (padrão 1)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_relatorio)

    g = sub.add_parser("pregoes", help="primeira/última barra e nº de barras de cada dia (CSV)")
    g.add_argument("arquivo")
    g.set_defaults(func=cmd_pregoes)

    v = sub.add_parser(
        "gaps", help="maiores saltos fechamento -> abertura seguinte (rolagem, eventos)"
    )
    v.add_argument("arquivo")
    v.add_argument("--top", type=int, default=15)
    v.set_defaults(func=cmd_gaps)

    x = sub.add_parser(
        "remover-incompletos", parents=[pregao], help="descarta pregões cortados nas pontas"
    )
    x.add_argument("arquivo")
    x.add_argument("--saida", required=True, help=".csv (formato MT5) ou .parquet")
    x.add_argument("--remover-internos", action="store_true", help=_AJUDA_INTERNOS)
    x.set_defaults(func=cmd_remover_incompletos)

    a = sub.add_parser("reamostrar", parents=[pregao], help="M1 -> M5/M15/...")
    a.add_argument("arquivo")
    a.add_argument("--minutos", type=int, required=True)
    a.add_argument("--saida", required=True, help=".parquet ou .csv")
    a.add_argument(
        "--remover-incompletos", action="store_true", help="descartar pregões cortados nas pontas"
    )
    a.add_argument("--remover-internos", action="store_true", help=_AJUDA_INTERNOS)
    a.set_defaults(func=cmd_reamostrar)

    c = sub.add_parser("validar-config", help="valida config/risk.yaml")
    c.add_argument("arquivo", nargs="?", default="config/risk.yaml")
    c.set_defaults(func=cmd_validar_config)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
