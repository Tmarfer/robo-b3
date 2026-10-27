"""Linha de comando: `robob3 <comando> ...`."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from robob3.config import carregar_config
from robob3.data import avaliar_barras, ler_barras_mt5, reamostrar


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def cmd_relatorio(args: argparse.Namespace) -> int:
    caminho = Path(args.arquivo)
    df = ler_barras_mt5(caminho)
    rel = avaliar_barras(df, minutos=args.minutos)
    meta = {"arquivo": caminho.name, "sha256": _sha256(caminho)}
    if args.json:
        print(json.dumps(meta | rel.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("\n".join(f"{k}: {v}" for k, v in meta.items()))
        print(rel.to_texto())
    return 0


def cmd_reamostrar(args: argparse.Namespace) -> int:
    df = ler_barras_mt5(args.arquivo)
    out = reamostrar(df, args.minutos)
    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    if saida.suffix == ".parquet":
        out.to_parquet(saida)
    else:
        out.to_csv(saida)
    print(f"{len(df)} barras -> {len(out)} barras M{args.minutos}: {saida}")
    return 0


def cmd_validar_config(args: argparse.Namespace) -> int:
    cfg = carregar_config(args.arquivo)
    print(json.dumps(cfg.model_dump(mode="json"), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="robob3")
    sub = p.add_subparsers(dest="comando", required=True)

    r = sub.add_parser("relatorio-dados", help="qualidade de um CSV de barras do MT5")
    r.add_argument("arquivo")
    r.add_argument("--minutos", type=int, default=1, help="timeframe do arquivo (padrão 1)")
    r.add_argument("--json", action="store_true")
    r.set_defaults(func=cmd_relatorio)

    a = sub.add_parser("reamostrar", help="M1 -> M5/M15/...")
    a.add_argument("arquivo")
    a.add_argument("--minutos", type=int, required=True)
    a.add_argument("--saida", required=True, help=".parquet ou .csv")
    a.set_defaults(func=cmd_reamostrar)

    c = sub.add_parser("validar-config", help="valida config/risk.yaml")
    c.add_argument("arquivo", nargs="?", default="config/risk.yaml")
    c.set_defaults(func=cmd_validar_config)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
