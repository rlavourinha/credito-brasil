# -*- coding: utf-8 -*-
"""
dados_deck.py — extrai todas as séries do dashboard-bcb para o deck.
Saída: _dados.json (datas ISO YYYY-MM, valores float).
Fontes: API SGS/BCB, IF.data (via ifdata.py), SCR V2 (CSV local),
snapshots BIS/OCDE (data/), npl.py (reconstrução NPL = saldo x taxa).
"""
import sys, json, warnings
from pathlib import Path

import pandas as pd

DASH = Path(r"D:\rlavourinha\Pictures\OneDrive\Área de Trabalho\Claude\dashboard")
sys.path.insert(0, str(DASH))
warnings.filterwarnings("ignore")

import data_loader as dl
import npl, ifdata
import internacional as intl

OUT = Path(__file__).parent / "_dados.json"
D = {}


def serie(df, col="v"):
    d = df.dropna(subset=[col]) if col in df.columns else df
    return [[p.strftime("%Y-%m"), round(float(x), 4)] for p, x in zip(d["periodo"], d[col])]


def sgs(cod, fator=1.0, inicio="01/01/2011"):
    s = dl.carregar_sgs(cod, "v", inicio=inicio)
    if fator != 1:
        s["v"] = s["v"] * fator
    return serie(s)


print("SGS panorama...")
D["saldo_total"] = sgs(20539, 0.001)      # R$ bi
D["saldo_livre"] = sgs(20542, 0.001)
D["saldo_dir"] = sgs(20593, 0.001)
D["conc_pf"] = sgs(20633, 0.001)          # concessões PF R$ bi
D["taxa_pf"] = sgs(20716)
D["taxa_pj"] = sgs(20715)
D["icc_pf"] = sgs(25353)
D["selic"] = serie(dl.carregar_selic(2011).rename(columns={"Selic (% a.a.)": "v"}))

print("SGS inadimplência / tomador...")
D["inad_pf_sfn"] = sgs(21084)
D["inad_pf_livre"] = sgs(21112)
D["atraso_curto"] = sgs(21005)
D["comprometimento"] = sgs(29034, inicio="01/01/2005")
D["comp_juros"] = sgs(29264, inicio="01/01/2005")
D["comp_amort"] = sgs(29263, inicio="01/01/2005")
D["endividamento"] = sgs(29037, inicio="01/01/2005")

print("NPL (reconstrução saldo x taxa)...")
df = npl.carregar()
d = df.set_index("periodo")
D["npl_total"] = [[p.strftime("%Y-%m"), round(float(x), 2)]
                  for p, x in d["NPL|Total PF"].dropna().items()]
core = npl.inad_ajustada(df, ["🌾 Rural", "💼 Consignado privado"])
core.index = df["periodo"]
D["inad_core"] = [[p.strftime("%Y-%m"), round(float(x), 3)] for p, x in core.dropna().items()]

for nome, key in [("🌾 Rural", "rural"), ("💼 Consignado privado", "consig"),
                  ("💳 Cartão de crédito", "cartao"), ("👤 Pessoal não consignado", "pessoal"),
                  ("🏧 Cheque especial", "cheque"), ("🚗 Veículos", "veiculos"),
                  ("🏠 Imobiliário", "imob")]:
    D[f"inad_{key}"] = [[p.strftime("%Y-%m"), round(float(x), 3)]
                        for p, x in d[f"Inad|{nome}"].dropna().items()]
    D[f"saldo_{key}"] = [[p.strftime("%Y-%m"), round(float(x), 2)]
                        for p, x in d[f"Saldo|{nome}"].dropna().items()]
D["npl_rural"] = [[p.strftime("%Y-%m"), round(float(x), 2)]
                  for p, x in d["NPL|🌾 Rural"].dropna().items()]
D["inad_rotativo"] = sgs(21127)

contr = npl.contribuicoes_12m(df).set_index("periodo").iloc[-1].dropna()
D["contrib_12m"] = {k: round(float(v), 3) for k, v in contr.items()}
D["contrib_ref"] = df["periodo"].max().strftime("%Y-%m")

print("IF.data (baixas)...")
fi = ifdata.carregar().set_index("periodo").sort_index()
inad_sfn = dl.carregar_sgs(21082, "v", inicio="01/01/2015").set_index("periodo")["v"]
fi["inad_sfn"] = inad_sfn.reindex(fi.index)
fi["npl_sist"] = fi["inad_sfn"] * fi["carteira"] / 100
fi["baixas_pct_npl"] = fi["baixas_tri"] / fi["npl_sist"].shift(1) * 4 * 100  # anualizado
fi["cobertura"] = fi["provisao"] / fi["npl_sist"] * 100
for k, col, r in [("baixas_tri", "baixas_tri", 1), ("baixas_pct", "baixas_pct_aa", 2),
                  ("pdd_tri", "despesa_pdd_tri", 1), ("pdd_pct", "despesa_pct_aa", 2),
                  ("prov_pct", "provisao_pct", 2), ("baixas_pct_npl", "baixas_pct_npl", 1),
                  ("cobertura", "cobertura", 1)]:
    D[f"ifd_{k}"] = [[p.strftime("%Y-%m"), round(float(x), r)]
                     for p, x in fi[col].dropna().items()]

print("SCR V2...")
v2 = pd.read_csv(DASH / "data" / "scr_v2_modalidade.csv")
v2["periodo"] = pd.to_datetime(v2["anomes"].astype(int).astype(str), format="%Y%m")
D["scr_inad"] = [[p.strftime("%Y-%m"), round(float(x), 2)]
                 for p, x in zip(v2["periodo"], v2["👤 Empréstimos PF|inad"]) if pd.notna(x)]
D["scr_ap"] = [[p.strftime("%Y-%m"), round(float(x), 2)]
               for p, x in zip(v2["periodo"], v2["👤 Empréstimos PF|ativo_prob"]) if pd.notna(x)]

print("Projeções...")
ex = npl.inad_ajustada(df, ["🌾 Rural"])
ex.index = df["periodo"]
D["inad_exagro"] = [[p.strftime("%Y-%m"), round(float(x), 3)] for p, x in ex.dropna().items()]
hist = pd.read_csv(DASH / "data" / "projecoes_hist.csv", parse_dates=["vintage", "alvo_mes"])
h = hist[hist["alvo"] == "ex-agro"]
D["proj_safras"] = [
    {"vintage": v.strftime("%Y-%m"),
     "pts": [[r["alvo_mes"].strftime("%Y-%m"), round(float(r["proj"]), 3),
              round(float(r["banda"]), 3)] for _, r in g.sort_values("alvo_mes").iterrows()]}
    for v, g in h.groupby("vintage")]

print("Internacional (BIS/OCDE)...")
raw = pd.read_csv(DASH / "data" / "bis_dsr.csv", header=None,
                  names=["borr", "pais", "tri", "v"])
p = raw[raw["borr"] == "P"].copy()
ult_tri = p.groupby("pais")["tri"].max()
D["bis_tri"] = str(p["tri"].max())
D["dsr_rank"] = sorted(
    [[c, float(p[(p["pais"] == c) & (p["tri"] == t)]["v"].iloc[0])] for c, t in ult_tri.items()],
    key=lambda t: -t[1])
D["dsr_br"] = [[t, float(v)] for t, v in
               p[p["pais"] == "BR"].sort_values("tri")[["tri", "v"]].values]

cred = pd.read_csv(DASH / "data" / "bis_priv_credit_gdp.csv", header=None,
                   names=["pais", "tri", "v"])
ultc = cred.dropna(subset=["v"]).groupby("pais").tail(1)
D["cred_gdp"] = {r["pais"]: round(float(r["v"]), 1) for _, r in ultc.iterrows()}

hh = pd.read_csv(DASH / "data" / "bis_hh_credit_gdp.csv", header=None,
                 names=["pais", "tri", "v"])
D["hh_gdp"] = {r["pais"]: round(float(r["v"]), 1)
               for _, r in hh.dropna(subset=["v"]).groupby("pais").tail(1).iterrows()}

D["icc_decomp"] = {"ref": intl.DECOMP_ICC_BR["ref"],
                   "comp": [[n, float(v)] for n, v, _ in intl.DECOMP_ICC_BR["componentes"]]}

print("Cronograma...")
import cronograma
_a, _m = map(int, D["inad_pf_sfn"][-1][0].split("-"))
_r = cronograma.proxima_divulgacao(_a, _m)
D["proxima_nota"] = {"data": _r["data"].isoformat(), "confirmada": _r["confirmada"], "hora": _r["hora"]}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(D, f, ensure_ascii=False)
print(f"OK -> {OUT.name}: {len(D)} chaves")
for k in ["inad_pf_sfn", "npl_total", "ifd_baixas_tri", "dsr_br"]:
    print(f"  {k}: {len(D[k])} pontos, último {D[k][-1]}")
