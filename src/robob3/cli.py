"""Linha de comando: `robob3 <comando> ...`."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import time
from pathlib import Path

from robob3.backtest import PERIODOS, ParametrosORB, backtest_orb, entrada_aleatoria, resumo
from robob3.config import carregar_config
from robob3.data import (
    ajustar_rolagem,
    avaliar_barras,
    candidatas_rolagem,
    carregar_rolagens,
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
        "janela": args.janela,
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


def cmd_rolagens_candidatas(args: argparse.Namespace) -> int:
    cands = candidatas_rolagem(ler_barras_mt5(args.arquivo), args.regra)

    def pct(x):
        return "" if x is None else f"{x:+.2f}"

    print("data,regra,gap_pct,gap_pct_anterior,gap_pct_seguinte,situacao")
    for c in cands:
        situacao = "confirmada" if c.confirmada else "pendente"
        print(
            f"{c.data},{c.regra},{pct(c.gap_pct)},{pct(c.gap_pct_anterior)},"
            f"{pct(c.gap_pct_seguinte)},{situacao}"
        )
    ok = [c.data for c in cands if c.confirmada]
    pend = [c.data for c in cands if not c.confirmada]
    print(f"\n# {len(cands)} candidatas: {len(ok)} confirmadas, {len(pend)} pendentes")
    print("# conferir antes de copiar para config/rolagens.yaml")
    print(f"datas: [{', '.join(ok)}]")
    print(f"pendentes: [{', '.join(pend)}]")
    return 0


def cmd_ajustar_rolagem(args: argparse.Namespace) -> int:
    rol = carregar_rolagens(args.ativo, args.config)
    df = ler_barras_mt5(args.arquivo)
    ajustada, ajustes = ajustar_rolagem(df, rol.datas, args.metodo)
    print(f"{rol.simbolo} — {rol.regra} — método {args.metodo}")
    for a in ajustes:
        if a.situacao == "aplicado":
            print(f"  {a.data}: {a.fech_anterior:g} -> {a.abertura:g}, salto {a.salto:+.6g}")
        else:
            print(f"  {a.data}: {a.situacao}")
    for d in rol.pendentes:
        print(f"  AVISO: rolagem pendente de confirmação em {d} — sem ajuste")
    saida = Path(args.saida)
    _gravar(ajustada, saida, formato_mt5=True)
    print(f"{len(ajustada)} barras: {saida}")
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


GRADE_ORB = [(s, a) for s in (150, 200, 300) for a in (1.5, 2.0, 3.0)]


def cmd_backtest_orb(args: argparse.Namespace) -> int:
    if args.periodo == "fora-da-amostra" and not args.confirmo_fora_da_amostra:
        print(
            "O período fora da amostra roda UMA vez, com a combinação escolhida no\n"
            "desenvolvimento. Se é isso, repita com --confirmo-fora-da-amostra."
        )
        return 2
    inicio, fim = PERIODOS[args.periodo]
    df = ler_barras_mt5(args.arquivo)
    print(
        f"win-orb-v1 | {args.periodo}: {inicio} a {fim} | custo R$ {args.custo:.2f}/lado | "
        f"barras ambíguas: {args.ambiguidade}"
    )

    if args.grade:
        print(
            "stop,alvo,operacoes,resultado_brl,resultado_custo_0.50,fator_lucro,acerto_pct,"
            "drawdown_max,ambiguas,por_ano"
        )
        for stop, alvo in GRADE_ORB:
            p = ParametrosORB(
                stop=stop, alvo=alvo, custo_lado=args.custo, ambiguidade=args.ambiguidade
            )
            r = resumo(backtest_orb(df, p, inicio, fim).operacoes)
            if not r["operacoes"]:
                print(f"{stop:g},{alvo:g},0")
                continue
            estresse = r["resultado_brl"] - r["operacoes"] * 2 * (0.50 - args.custo)
            anos = " ".join(f"{a}:{v:+.2f}" for a, v in r["por_ano"].items())
            print(
                f"{stop:g},{alvo:g},{r['operacoes']},{r['resultado_brl']:.2f},{estresse:.2f},"
                f"{r['fator_lucro']},{r['acerto_pct']},{r['drawdown_max']:.2f},"
                f"{r['ambiguas']},{anos}"
            )
        return 0

    p = ParametrosORB(
        stop=args.stop, alvo=args.alvo, custo_lado=args.custo, ambiguidade=args.ambiguidade
    )
    res = backtest_orb(df, p, inicio, fim)
    r = resumo(res.operacoes)
    params = {"stop": p.stop, "alvo": p.alvo, "custo_lado": p.custo_lado}
    saida = {"parametros": params | {"ambiguidade": p.ambiguidade}} | r
    if r["operacoes"]:
        saida["resultado_custo_0.50"] = round(
            r["resultado_brl"] - r["operacoes"] * 2 * (0.50 - args.custo), 2
        )
        saida["dias_sem_operacao"] = res.sem_operacao["motivo"].value_counts().to_dict()
        if args.aleatorio:
            saida["entrada_aleatoria"] = entrada_aleatoria(df, res, sorteios=args.aleatorio)
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    if args.operacoes:
        destino = Path(args.operacoes)
        destino.parent.mkdir(parents=True, exist_ok=True)
        res.operacoes.to_csv(destino, index=False)
        print(f"operações: {destino}")
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
    pregao.add_argument(
        "--janela", type=int, default=5, help="pregões vizinhos de cada lado (padrão 5)"
    )

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

    k = sub.add_parser(
        "rolagens-candidatas", help="datas prováveis de troca de contrato pela regra do ativo"
    )
    k.add_argument("arquivo")
    k.add_argument("--regra", choices=["win", "wdo"], required=True)
    k.set_defaults(func=cmd_rolagens_candidatas)

    j = sub.add_parser(
        "ajustar-rolagem", help="retroajusta a série contínua nas datas de config/rolagens.yaml"
    )
    j.add_argument("arquivo")
    j.add_argument("--ativo", required=True, help="chave em config/rolagens.yaml (WIN, WDO)")
    j.add_argument("--saida", required=True, help=".csv (formato MT5) ou .parquet")
    j.add_argument("--metodo", choices=["aditivo", "razao"], default="aditivo")
    j.add_argument("--config", default="config/rolagens.yaml")
    j.set_defaults(func=cmd_ajustar_rolagem)

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

    b = sub.add_parser("backtest-orb", help="backtest da win-orb-v1 (docs/estrategias)")
    b.add_argument("arquivo", help="CSV M5 do WIN (formato MT5)")
    b.add_argument("--periodo", choices=sorted(PERIODOS), default="desenvolvimento")
    b.add_argument("--confirmo-fora-da-amostra", action="store_true")
    b.add_argument("--grade", action="store_true", help="as 9 combinações da especificação")
    b.add_argument("--stop", type=float, default=200)
    b.add_argument("--alvo", type=float, default=2.0, help="múltiplo do stop")
    b.add_argument("--custo", type=float, default=0.25, help="R$ por contrato por lado")
    b.add_argument("--aleatorio", type=int, default=1000, help="sorteios (0 = não rodar)")
    b.add_argument("--operacoes", help="CSV de saída com cada operação")
    b.add_argument(
        "--ambiguidade",
        choices=["conservadora", "otimista"],
        default="conservadora",
        help="otimista = só diagnóstico (barras ambíguas a favor); a avaliação é a conservadora",
    )
    b.set_defaults(func=cmd_backtest_orb)

    c = sub.add_parser("validar-config", help="valida config/risk.yaml")
    c.add_argument("arquivo", nargs="?", default="config/risk.yaml")
    c.set_defaults(func=cmd_validar_config)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
