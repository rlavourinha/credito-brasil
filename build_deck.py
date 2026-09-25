# -*- coding: utf-8 -*-
"""
build_deck.py — gera index.html (deck "Crédito no Brasil") a partir de _dados.json.
Padrão visual do deck Cyrela (Fraunces itálico, scroll-snap, SVG inline, sem CDN de JS).
Template montado com .replace(sentinela) — nunca str.format em HTML com CSS/JS.
"""
import json
import datetime as dt
from pathlib import Path

RAIZ = Path(__file__).parent
D = json.load(open(RAIZ / "_dados.json", encoding="utf-8"))

VERSAO = "1.1"
HOJE = dt.date.today().strftime("%d/%m/%Y")

# ── util de série ──────────────────────────────────────────────────────────────
def _ord(ym):  # "2026-07" -> meses desde 2000
    a, m = ym.split("-")[:2]
    return int(a) * 12 + int(m)

def val(key):            # último valor
    return D[key][-1][1]

def em(key, ym):
    for p, v in D[key]:
        if p == ym:
            return v
    return None

def var12(key):
    pts = D[key]
    return (pts[-1][1] / pts[-13][1] - 1) * 100

def serie_var12(key, ini="2012-01"):
    pts = D[key]
    out = []
    for i in range(12, len(pts)):
        if pts[i][0] >= ini and _ord(pts[i][0]) - _ord(pts[i - 12][0]) == 12:
            out.append([pts[i][0], (pts[i][1] / pts[i - 12][1] - 1) * 100])
    return out

def mm12(key):
    pts = D[key]
    return [[pts[i][0], sum(v for _, v in pts[i - 11:i + 1]) / 12]
            for i in range(11, len(pts))]

def desde(key, ini):
    return [p for p in D[key] if p[0] >= ini]

# ── janelas de visualização (tudo / 5a / 2a) ──────────────────────────────────
JANELAS = [("tudo", None, "tudo"), ("5a", 60, "5 anos"), ("2a", 24, "2 anos")]

def ym_menos(ym, k):
    o = _ord(ym) - k
    a = (o - 1) // 12
    return f"{a:04d}-{o - a * 12:02d}"

def rlinhas(series, ann=None, band=None, ylim=None, **kw):
    """Render adiável de linhas(): fn(meses|None) -> svg. Janela curta corta as
    séries, filtra anotações fora dela e libera o Y para reescalar (detalhe da ponta)."""
    def r(meses):
        if meses is None:
            return linhas(series, ann=ann, band=band, ylim=ylim, **kw)
        ult = max(s["pts"][-1][0] for s in series if s["pts"])
        ini = ym_menos(ult, meses - 1)
        ss = [dict(s, pts=[p for p in s["pts"] if p[0] >= ini]) for s in series]
        ss = [s for s in ss if len(s["pts"]) >= 2]
        aa = [a for a in (ann or []) if a["ym"] >= ini] or None
        bb = dict(band, pts=[p for p in band["pts"] if p[0] >= ini]) if band else None
        return linhas(ss, ann=aa, band=bb, ylim=None, **kw)
    return r

def rbarras_tri(pts, **kw):
    def r(meses):
        pp = pts if meses is None else [p for p in pts if p[0] >= ym_menos(pts[-1][0], meses - 1)]
        return barras_tri(pp, **kw)
    return r

def com_janelas(renders, layout):
    """Pré-renderiza cada janela e monta o seletor; só a variante ativa fica visível."""
    partes = []
    for i, (key, meses, rot) in enumerate(JANELAS):
        svgs = [r(meses) for r in renders]
        style = "" if i == 0 else ' style="display:none"'
        partes.append(f'<div class="winvar" data-win="{key}"{style}>{layout(svgs)}</div>')
    seg = '<div class="seg winseg" role="group" aria-label="janela">' + "".join(
        f'<button data-win="{k}"{" class=char_on" if i == 0 else ""}>{r}</button>'
        for i, (k, m, r) in enumerate(JANELAS)) + "</div>"
    seg = seg.replace("class=char_on", 'class="on"')
    return f'<div class="wingrp">{seg}{"".join(partes)}</div>'

def jan1(series, **kw):
    return com_janelas([rlinhas(series, **kw)], lambda s: viz(s[0]))

# ── helpers de gráfico (idioma do deck Cyrela) ────────────────────────────────
def _ticks(vmin, vmax, alvo=5):
    import math
    span = vmax - vmin
    if span <= 0:
        span = abs(vmax) or 1
    bruto = span / alvo
    mag = 10 ** math.floor(math.log10(bruto))
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * mag:
            passo = m * mag
            break
    lo = math.floor(vmin / passo) * passo
    hi = math.ceil(vmax / passo) * passo
    n = int(round((hi - lo) / passo))
    return [lo + i * passo for i in range(n + 1)]

def _fmt(v, dec=None):
    if dec is None:
        dec = 0 if abs(v) >= 100 or v == int(v) else 1
    s = f"{v:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s

def linhas(series, W=980, H=430, title="", sub="", unit="", ylim=None,
           ann=None, band=None, x1=None, ylab_dec=None, hoje_linha=None):
    """series: [{pts, cor, dash, rot, dec}]  band: {pts:[[ym,lo,hi]], cor}"""
    top, bot, x0 = 52, H - 26, 60
    rots = any(s.get("rot") for s in series)
    if x1 is None:
        x1 = W - (170 if rots else 50)
    tudo = [v for s in series for _, v in s["pts"]]
    if band:
        tudo += [v for _, lo, hi in band["pts"] for v in (lo, hi)]
    vmin, vmax = min(tudo), max(tudo)
    if ylim:
        vmin, vmax = ylim
    tk = _ticks(vmin, vmax, 4 if H < 260 else 5)
    vmin, vmax = tk[0], tk[-1]
    os_ = [_ord(p) for s in series for p, _ in s["pts"]]
    if band:
        os_ += [_ord(p) for p, _, _ in band["pts"]]
    o0, o1 = min(os_), max(os_)
    def X(ym): return x0 + (_ord(ym) - o0) / max(o1 - o0, 1) * (x1 - x0)
    def Y(v): return bot - (v - vmin) / (vmax - vmin) * (bot - top)

    g = [f'<text x="{x0}" y="18" class="gtit">{title}</text>']
    if sub:
        g.append(f'<text x="{x0}" y="34" class="gsub">{sub}</text>')
    for t in tk:
        y = Y(t)
        g.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="var(--grid)" opacity=".55"/>')
        g.append(f'<text x="{x0-6}" y="{y+4:.1f}" class="axq" text-anchor="end" opacity=".85">{_fmt(t, ylab_dec)}{unit}</text>')
    g.append(f'<line x1="{x0}" y1="{Y(max(vmin,0) if vmin<0<vmax else vmin):.1f}" x2="{x1}" y2="{Y(max(vmin,0) if vmin<0<vmax else vmin):.1f}" stroke="var(--baseline)"/>')
    import math
    anos = range(o0 // 12, o1 // 12 + 1)
    # nº de rótulos de ano proporcional à largura útil (evita colisão nos minis de 480px)
    n_alvo = max(3, int((x1 - x0) / 85))
    passo_ano = max(1, math.ceil((o1 - o0) / 12 / n_alvo))
    for a in anos:
        if a % passo_ano:
            continue
        o = a * 12 + 1
        if o < o0 or o > o1:
            continue
        g.append(f'<text x="{X(f"{a}-01"):.1f}" y="{bot+17}" class="axq" text-anchor="middle" opacity=".75">{a}</text>')
    if band:
        cima = " ".join(f"{X(p):.1f},{Y(hi):.1f}" for p, _, hi in band["pts"])
        baixo = " ".join(f"{X(p):.1f},{Y(lo):.1f}" for p, lo, _ in reversed(band["pts"]))
        g.append(f'<polygon points="{cima} {baixo}" fill="{band.get("cor","var(--s1)")}" opacity=".12"/>')
    fins = []
    for s in series:
        pts = s["pts"]
        poly = " ".join(f"{X(p):.1f},{Y(v):.1f}" for p, v in pts)
        dash = f' stroke-dasharray="{s["dash"]}"' if s.get("dash") else ""
        g.append(f'<polyline points="{poly}" fill="none" stroke="{s["cor"]}" stroke-width="{s.get("w",2.2)}"{dash}/>')
        px, pv = pts[-1]
        g.append(f'<circle cx="{X(px):.1f}" cy="{Y(pv):.1f}" r="3.2" fill="{s["cor"]}"/>')
        if s.get("rot"):
            fins.append([Y(pv), s["cor"], s["rot"], pv, s.get("dec", 1)])
    fins.sort()
    for i in range(1, len(fins)):   # anti-colisão dos rótulos de fim de linha
        if fins[i][0] - fins[i - 1][0] < 15:
            fins[i][0] = fins[i - 1][0] + 15
    for y, cor, rot, pv, dec in fins:
        g.append(f'<text x="{x1+8}" y="{y+4:.1f}" style="font-size:10.5px;font-weight:650" fill="{cor}">{_fmt(pv,dec)}{unit} {rot}</text>')
    for a in (ann or []):
        ax, ay = X(a["ym"]), Y(a["v"])
        g.append(f'<circle cx="{ax:.1f}" cy="{ay:.1f}" r="3.4" fill="none" stroke="{a.get("cor","var(--ink-1)")}" stroke-width="1.4"/>')
        anch = a.get("anchor", "middle")
        g.append(f'<text x="{ax+a.get("dx",0):.1f}" y="{ay+a.get("dy",-10):.1f}" class="ann" fill="{a.get("cor","var(--ink-1)")}" text-anchor="{anch}">{a["t"]}</text>')
    return f'<svg viewBox="0 0 {W} {H}">' + "".join(g) + "</svg>"


def barras_h(itens, W=980, H=None, title="", sub="", unit="", dec=1, destaque=None):
    """itens: [(rotulo, valor, cor|None)]; destaque: rotulo em negrito."""
    n = len(itens)
    lh = 24 if n <= 16 else (17 if n <= 24 else 11.5)
    bh = lh - 7 if n <= 24 else lh - 6
    top = 56
    H = H or top + n * lh + 16
    x0, x1 = 205, W - 90
    vmax = max(v for _, v, *_ in itens)
    g = [f'<text x="12" y="18" class="gtit">{title}</text>']
    if sub:
        g.append(f'<text x="12" y="34" class="gsub">{sub}</text>')
    for i, it in enumerate(itens):
        rot, v = it[0], it[1]
        cor = it[2] if len(it) > 2 and it[2] else "var(--grid)"
        y = top + i * lh
        w = (x1 - x0) * v / vmax
        eh = destaque and destaque in rot
        fs = "10px" if n > 24 else ("11.5px" if n > 16 else "12.5px")
        peso = 750 if eh else 500
        g.append(f'<text x="{x0-8}" y="{y+lh*0.66:.1f}" text-anchor="end" style="font-size:{fs};font-weight:{peso}" fill="{"var(--s1)" if eh else "var(--ink-2)"}">{rot}</text>')
        g.append(f'<rect x="{x0}" y="{y+2.5}" width="{w:.1f}" height="{bh}" rx="3" fill="{"var(--s1)" if eh else cor}" opacity="{1 if eh else .8}"/>')
        g.append(f'<text x="{x0+w+7:.1f}" y="{y+lh*0.66:.1f}" style="font-size:{fs};font-weight:{700 if eh else 550}" fill="{"var(--s1)" if eh else "var(--ink-1)"}">{_fmt(v,dec)}{unit}</text>')
    return f'<svg viewBox="0 0 {W} {H}">' + "".join(g) + "</svg>"


def barras_tri(pts, W=980, H=400, title="", sub="", unit="", destaque_ym=None, nan_ym=None):
    """barras trimestrais; destaque no último; nan_ym: trimestre sem estimativa (hachura)."""
    top, bot, x0, x1 = 52, H - 26, 60, W - 30
    vmax = max(v for _, v in pts)
    tk = _ticks(0, vmax)
    vmax = tk[-1]
    n = len(pts)
    bw = (x1 - x0) / n * 0.66
    def X(i): return x0 + (i + 0.5) / n * (x1 - x0)
    def Y(v): return bot - v / vmax * (bot - top)
    g = [f'<text x="{x0}" y="18" class="gtit">{title}</text>',
         f'<text x="{x0}" y="34" class="gsub">{sub}</text>']
    for t in tk:
        g.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x1}" y2="{Y(t):.1f}" stroke="var(--grid)" opacity=".55"/>')
        g.append(f'<text x="{x0-6}" y="{Y(t)+4:.1f}" class="axq" text-anchor="end" opacity=".85">{_fmt(t)}</text>')
    g.append(f'<line x1="{x0}" y1="{bot}" x2="{x1}" y2="{bot}" stroke="var(--baseline)"/>')
    for i, (p, v) in enumerate(pts):
        eh = p == destaque_ym
        g.append(f'<rect x="{X(i)-bw/2:.1f}" y="{Y(v):.1f}" width="{bw:.1f}" height="{bot-Y(v):.1f}" rx="2" '
                 f'fill="{"var(--s1)" if eh else "var(--grid)"}" opacity="{1 if eh else .95}"/>')
        ano_novo = i == 0 or pts[i - 1][0][:4] != p[:4]
        if ano_novo and (len(pts) <= 24 or int(p[:4]) % 2 == 1):
            g.append(f'<text x="{X(i):.1f}" y="{bot+17}" class="axq" text-anchor="middle" opacity=".75">{p[:4]}</text>')
        if eh:
            g.append(f'<text x="{X(i):.1f}" y="{Y(v)-8:.1f}" class="blab" text-anchor="middle" fill="var(--s1)">{_fmt(v,1)}{unit}</text>')
    if nan_ym:
        i = next((j for j, (p, _) in enumerate(pts) if p > nan_ym), None)
        if i:
            g.append(f'<text x="{(X(i-1)+X(i))/2:.1f}" y="{bot-6:.1f}" class="axq" text-anchor="middle" opacity=".8">*</text>')
    return f'<svg viewBox="0 0 {W} {H}">' + "".join(g) + "</svg>"


def dispersao(itens, W=980, H=390, title="", sub="", xl="", abaixo=()):
    """itens: [(rotulo, x, y, destaque)]; abaixo: rótulos desenhados sob o ponto."""
    top, bot, x0, x1 = 52, H - 40, 70, W - 40
    xs = [x for _, x, _, _ in itens]
    ys = [y for _, _, y, _ in itens]
    tkx, tky = _ticks(min(xs) * 0.9, max(xs) * 1.05), _ticks(min(ys) * 0.9, max(ys) * 1.06)
    def X(v): return x0 + (v - tkx[0]) / (tkx[-1] - tkx[0]) * (x1 - x0)
    def Y(v): return bot - (v - tky[0]) / (tky[-1] - tky[0]) * (bot - top)
    g = [f'<text x="{x0}" y="18" class="gtit">{title}</text>',
         f'<text x="{x0}" y="34" class="gsub">{sub}</text>']
    for t in tky:
        g.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x1}" y2="{Y(t):.1f}" stroke="var(--grid)" opacity=".5"/>')
        g.append(f'<text x="{x0-6}" y="{Y(t)+4:.1f}" class="axq" text-anchor="end">{_fmt(t)}</text>')
    for t in tkx:
        g.append(f'<text x="{X(t):.1f}" y="{bot+18}" class="axq" text-anchor="middle">{_fmt(t)}</text>')
    g.append(f'<text x="{(x0+x1)/2:.0f}" y="{H-4}" class="gsub" text-anchor="middle">{xl}</text>')
    for rot, x, y, eh in itens:
        g.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{7 if eh else 4.5}" fill="{"var(--s1)" if eh else "var(--s2)"}" opacity="{1 if eh else .5}"/>')
        if eh or rot in ("Hong Kong", "Noruega", "Austrália", "Holanda", "EUA", "Turquia", "Coreia", "Suíça", "Canadá", "Índia", "México", "Alemanha", "Japão", "Suécia"):
            dy = 16 if rot in abaixo else -10
            g.append(f'<text x="{X(x):.1f}" y="{Y(y)+dy:.1f}" class="ann" text-anchor="middle" fill="{"var(--s1)" if eh else "var(--ink-2)"}" style="font-size:{12.5 if eh else 10.5}px">{rot}</text>')
    return f'<svg viewBox="0 0 {W} {H}">' + "".join(g) + "</svg>"


# ── montagem de slides ────────────────────────────────────────────────────────
SLIDES = []

def sec(kick, head, corpo, verde=None, nota=None, cls=""):
    v = ""
    if verde:
        msg, sub = verde
        v = ('<div class="sl-output"><span class="out-tag">leitura</span>'
             f'<span class="out-msg">{msg}</span>'
             + (f'<span class="out-sub">{sub}</span>' if sub else "") + "</div>")
    n = f'<p class="sl-nota">{nota}</p>' if nota else ""
    SLIDES.append(f'<section class="slide{(" "+cls) if cls else ""}"><div class="sl-in">'
                  f'<p class="kick">{kick}</p><h2 class="head-xl">{head}</h2>'
                  f'{corpo}{v}{n}</div></section>')

def viz(svg):
    return f'<div class="viz">{svg}</div>'

def duo(a, b):
    return f'<div class="fwgrid" style="margin-top:6px"><div>{a}</div><div>{b}</div></div>'

S1, S2, S3, MU = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)"

# valores correntes p/ texto
ULT = D["inad_pf_sfn"][-1][0]                     # 2026-07
ult_rot = "jul/26"
saldo = val("saldo_total")
inad = val("inad_pf_sfn")
comp = val("comprometimento")
dsr = D["dsr_br"][-1][1]
npl_hoje = val("npl_total")

# 1 ─ capa
SLIDES.append(f"""
<section class="slide" id="sl0"><div class="sl-in">
  <p class="kick">crédito no brasil · dados primários BCB · SGS + IF.data + SCR + BIS</p>
  <div class="ticker-hero">Crédito.<small>O ciclo de 2025-26: preço recorde, dois choques de safra — e a onda de baixas em curso. Tudo em dados primários, até julho/2026.</small></div>
  <div class="tiles">
    <div class="tile"><span class="n">R$ {_fmt(saldo/1000, 2)} tri</span><span class="l">carteira total do SFN · +{_fmt(var12("saldo_total"),1)}% em 12m</span></div>
    <div class="tile"><span class="n" style="color:var(--s1)">{_fmt(inad,2)}%</span><span class="l">inadimplência PF · recorde da série</span></div>
    <div class="tile"><span class="n">{_fmt(comp,1)}%</span><span class="l">renda comprometida · recorde</span></div>
    <div class="tile"><span class="n">{_fmt(dsr,1)}%</span><span class="l">DSR privado (BIS) · 2º maior do mundo</span></div>
  </div>
  <div class="chips2">
    <span class="chip2"><b>1</b> · o sistema</span><span class="chip2"><b>2</b> · a inadimplência recorde</span>
    <span class="chip2"><b>3</b> · baixas e provisões</span><span class="chip2"><b>4</b> · o tomador e o ciclo</span>
    <span class="chip2"><b>5</b> · o Brasil no mundo</span>
  </div>
  <div class="byline">Elaboração própria sobre <b>dados primários</b>: BCB/SGS (nota de estatísticas monetárias e de crédito), IF.data, SCR.data, Desenrola e BIS/OCDE/Banco Mundial · reconstruções: NPL = saldo × taxa; baixas = despesa de PDD − Δprovisão · <b>dashboard vivo</b>: dashboard-bcb (Streamlit)</div>
</div></section>""")

# 2 ─ panorama: crescimento do estoque
g = jan1([
    {"pts": serie_var12("saldo_total"), "cor": S1, "rot": "total", "dec": 1},
    {"pts": serie_var12("saldo_livre"), "cor": S2, "dash": "4 3", "rot": "livre", "dec": 1},
    {"pts": serie_var12("saldo_dir"), "cor": MU, "rot": "direcionado", "dec": 1},
], title="Crescimento do estoque de crédito (% em 12 meses)", sub="SGS 20539/20542/20593 · saldo total R$ %SALDO% bi em %ULT%".replace("%SALDO%", _fmt(saldo)).replace("%ULT%", ult_rot), unit="%", H=420)
sec("parte 1 · o sistema", "O crédito não parou de crescer.", g,
    verde=(f"+{_fmt(var12('saldo_total'),1)}% em 12 meses, com R$ {_fmt(saldo/1000,2)} tri de estoque — este não é um ciclo de escassez de crédito.",
           "É o denominador do índice de inadimplência: enquanto cresce ~10% a.a., dilui a taxa medida."),
    nota="Fonte: BCB/SGS. Var. % em 12m sobre o saldo nominal.")

# 3 ─ concessões PF (real + MM12)
g = jan1([
    {"pts": D["conc_pf"], "cor": MU, "w": 1.4, "rot": "real", "dec": 0},
    {"pts": mm12("conc_pf"), "cor": S1, "w": 2.6, "rot": "MM12", "dec": 0},
], title="Concessões de crédito PF (R$ bi/mês)", sub="SGS 20633 · número real (cinza) e média móvel 12m", H=410)
sec("parte 1 · o sistema", "Originação em máxima histórica.", g,
    verde=(f"R$ {_fmt(val('conc_pf'))} bi concedidos a PF em {ult_rot} — topo da série.",
           "Safra nova entra limpa no índice; o custo dela aparece 12-24 meses depois."),
    nota="Fonte: BCB/SGS. Concessões nominais mensais; MM12 pela regra da casa (nunca MM3).")

# 4 ─ preço
g = jan1([
    {"pts": D["taxa_pf"], "cor": S1, "rot": "taxa PF", "dec": 1},
    {"pts": D["taxa_pj"], "cor": S2, "dash": "4 3", "rot": "taxa PJ", "dec": 1},
    {"pts": D["selic"], "cor": MU, "rot": "Selic", "dec": 2},
], title="O preço do crédito (% a.a.)", sub="SGS 20716/20715 (taxas médias das concessões) e Selic meta", unit="%", H=390)
sec("parte 1 · o sistema", "A Selic cede. A taxa ao tomador, quase nada.", g,
    verde=(f"Taxa PF em {_fmt(val('taxa_pf'),1)}% a.a. com Selic a {_fmt(val('selic'),2)}% — o spread é o personagem central deste deck.",
           "Corte de ~1 p.p. na Selic em dez meses; o estoque reprecifica com anos de defasagem."),
    nota="Fonte: BCB/SGS. Taxas médias das novas concessões (recursos livres + direcionados).")

# 5 ─ inadimplência história
g = jan1([
    {"pts": D["inad_pf_sfn"], "cor": S1, "w": 2.6, "rot": "inad PF (SFN)", "dec": 2},
], title="Inadimplência PF — SFN total (% da carteira, atraso >90d)", sub="SGS 21084 · série completa desde 2011",
    unit="%", H=405, ylim=(2.5, 6.2),
    ann=[{"ym": "2012-05", "v": em("inad_pf_sfn", "2012-05"), "t": "pico 2012: 5,51", "dy": -12},
         {"ym": "2016-05", "v": em("inad_pf_sfn", "2016-05"), "t": "recessão 2016: 4,37", "dy": -12},
         {"ym": "2023-05", "v": em("inad_pf_sfn", "2023-05"), "t": "2023: 4,35", "dy": -12},
         {"ym": "2021-06", "v": em("inad_pf_sfn", "2021-06"), "t": "mínima pós-pandemia: 2,91", "dy": 16},
         {"ym": ULT, "v": inad, "t": f"{_fmt(inad,2)} · recorde", "dy": -12, "anchor": "end", "cor": S1}])
sec("parte 2 · a inadimplência recorde", "Nunca esteve tão alta.", g,
    verde=("5,81% — acima do pico de 2012 e 1,4 p.p. acima da recessão de 2016, com desemprego baixo.",
           "É inadimplência de pleno emprego: o motor é o preço da dívida, não a renda."),
    nota="Fonte: BCB/SGS 21084 (PF total: livre + direcionado). Metodologia atual começa em mar/2011.")

# 6 ─ NPL em R$
g = jan1([
    {"pts": D["npl_total"], "cor": S1, "w": 2.6, "rot": "NPL PF", "dec": 0},
], title="Estoque inadimplente PF em R$ bilhões (NPL = saldo × taxa)", sub="reconstrução própria sobre SGS · numerador do índice",
    H=410, ann=[{"ym": "2024-07", "v": em("npl_total", "2024-07"), "t": "24m: R$ 142 bi", "dy": -12},
                {"ym": ULT, "v": npl_hoje, "t": f"R$ {_fmt(npl_hoje)} bi (+38% em 12m)", "dy": -12, "anchor": "end", "cor": S1}])
sec("parte 2 · a inadimplência recorde", "O estoque quase dobrou em dois anos.", g,
    verde=("R$ 270 bi em atraso: +38% em 12 meses, +90% em 24 — contra carteira crescendo 11%.",
           "Sobre a carteira de um ano atrás, o índice seria 6,44%: o crescimento do denominador dilui 0,6 p.p."),
    nota="NPL_i = saldo_i × inadimplência_i, como o BCB constrói o numerador do índice (atraso >90d).")

# 7 ─ total × core
g = jan1([
    {"pts": D["inad_pf_sfn"], "cor": S1, "w": 2.6, "rot": "PF total", "dec": 2},
    {"pts": D["inad_core"], "cor": S2, "w": 2.2, "dash": "5 3", "rot": "core", "dec": 2},
], title="Total × core — inadimplência PF sem os dois choques (%)", sub="core = (NPL − rural − consignado privado) ÷ (saldo − rural − consignado privado)",
    unit="%", H=390, ylim=(2.5, 6.2),
    ann=[{"ym": "2012-05", "v": em("inad_core", "2012-05"), "t": "pico do core em 2012: 5,88", "dy": 18, "cor": S2}])
sec("parte 2 · a inadimplência recorde", "Sem agro e consignado novo, ainda não é 2012.", g,
    verde=(f"O core está em {_fmt(val('inad_core'),2)}% — maior nível desde 2012, abaixo do pico de 5,88%.",
           "O recorde do agregado = core pressionado + dois choques concentrados."),
    nota="Reconstrução própria sobre SGS (npl.py do dashboard-bcb). Consignado privado ≠ consignado INSS/público.")

# 8 ─ contribuições
c = D["contrib_12m"]
ordem = [(k, v) for k, v in c.items() if not k.startswith("Δ")]
ordem.sort(key=lambda t: -t[1])
tot = c.get("Δ Inadimplência PF (12m)", sum(v for _, v in ordem))
itens = [(f"{k.split(' ', 1)[-1] if k[0] in '🌾💼💳👤🏧🚗🏠' else k}", round(v, 2),
          S1 if v == max(v2 for _, v2 in ordem) else None) for k, v in ordem]
g = barras_h([(r, v, cr) for r, v, cr in itens if v >= 0.01], W=980,
             title=f"Quem explica os +{_fmt(tot,2)} p.p. em 12 meses (contribuição, p.p.)",
             sub=f"decomposição exata do Δ12m do índice PF · {ult_rot} · Demais PF ≈ 0 (omitido)", unit=" p.p.", dec=2, destaque="Rural")
sec("parte 2 · a inadimplência recorde", "Metade da alta vem de dois bolsos.", viz(g),
    verde=("Rural (+0,48) e consignado privado (+0,18): 14% da carteira explicando ~45% da alta do estoque inadimplente.",
           "O resto é a máquina cara de sempre — cartão, pessoal, cheque — subindo devagar."),
    nota="Decomposição: Δinad = Σ [NPL_i(t)/S(t) − NPL_i(t−12)/S(t−12)] — soma exatamente o Δ do índice.")

# 9 ─ rural
ga = rlinhas([{"pts": D["inad_rural"], "cor": S1, "w": 2.4, "rot": "inad", "dec": 2}],
            W=480, H=330, title="Inadimplência rural PF (%)", sub="SGS 21148 · 4,47% → 8,79% em 12m", unit="%")
gb = rlinhas([{"pts": D["npl_rural"], "cor": S2, "w": 2.4, "rot": "NPL", "dec": 0}],
            W=480, H=330, title="NPL rural PF (R$ bi)", sub="+105% em 12m, carteira +4% (parada)")
sec("parte 2 · a inadimplência recorde", "O campo quebrou primeiro: crise de solvência.", com_janelas([ga, gb], lambda v: duo(viz(v[0]), viz(v[1]))),
    verde=("Inadimplência dobrou em 12 meses com a carteira parada — os bancos já fecharam a torneira do agro.",
           "R$ 49 bi de NPL rural; ativo problemático no SCR a 10,3% diz que há mais atrás dos 90 dias."),
    nota="Fonte: BCB/SGS 20609/21148. Contexto: renda agrícola em queda e onda de RJs de produtores 2024-26.")

# 10 ─ consignado privado
ga = rlinhas([{"pts": D["saldo_consig"], "cor": S1, "w": 2.4, "rot": "saldo", "dec": 0}],
            W=480, H=330, title="Saldo consignado privado (R$ bi)", sub="SGS 20576 · R$ 40 bi (dez/24) → R$ 118 bi",
            ann=[{"ym": "2025-03", "v": em("saldo_consig", "2025-03"), "t": "Crédito do Trabalhador", "dy": -14, "dx": 6, "anchor": "end"}])
gb = rlinhas([{"pts": D["inad_consig"], "cor": S2, "w": 2.4, "rot": "inad", "dec": 2}],
            W=480, H=330, title="Inadimplência (%)", sub="SGS 21116 · consignado privado · 6,17% → 10,03% em 12m", unit="%")
sec("parte 2 · a inadimplência recorde", "A safra nova: o book triplicou — e já azeda.", com_janelas([ga, gb], lambda v: duo(viz(v[0]), viz(v[1]))),
    verde=("10% de inadimplência num book em que a maior parte dos contratos nem completou um ano.",
           "NPL +283% em 12m. O denominador verde disfarça: as coortes maduras rodam bem acima de 10%. A garantia quebra na rotatividade CLT."),
    nota="Fonte: BCB/SGS. Programa Crédito do Trabalhador (eSocial) lançado em mar/2025; consignado INSS não incluído.")

# 11 ─ máquina cara (4 minis)
minis = []
for key, tit, cod in [("inad_rotativo", "Cartão rotativo", 21127), ("inad_cheque", "Cheque especial", 21113),
                      ("inad_pessoal", "Pessoal não consignado", 21114), ("inad_cartao", "Cartão total", 21129)]:
    minis.append(rlinhas([{"pts": D[key], "cor": S1, "w": 2.2, "rot": "", "dec": 1}],
                         W=480, H=178, title=f"{tit} (%)", sub=f"SGS {cod} · hoje: {_fmt(val(key),1)}%", unit="%"))
corpo = com_janelas(minis, lambda v: f'<div class="fwgrid" style="margin-top:6px"><div>{viz(v[0])}</div><div>{viz(v[1])}</div><div>{viz(v[2])}</div><div>{viz(v[3])}</div></div>')
sec("parte 2 · a inadimplência recorde", "E a máquina cara de sempre segue moendo.", corpo,
    verde=("Rotativo: 65,9% do saldo em atraso >90d — recorde.",
           "O crédito caro do dia a dia sobe devagar, sem choque: pano de fundo estrutural."),
    nota="Fonte: BCB/SGS (recursos livres PF). Quatro escalas diferentes — leia os níveis, não compare as alturas.")

# 12 ─ SCR: inad vs AP
g = linhas([
    {"pts": D["scr_ap"], "cor": S1, "w": 2.4, "rot": "ativo problemático", "dec": 1},
    {"pts": D["scr_inad"], "cor": S2, "w": 2.4, "dash": "4 3", "rot": "inadimplência", "dec": 1},
], title="Empréstimos PF no SCR: inadimplência × ativo problemático (%)", sub="SCR.data (Res. 4.966) · jan/25 em diante · gap ≈ estável",
    unit="%", H=390)
sec("parte 2 · a inadimplência recorde", "Não é a régua contábil: é fluxo.", viz(g),
    verde=("O gap entre ativo problemático e inadimplência ficou estável — as duas métricas sobem juntas em 2026.",
           f"A Res. 4.966 deslocou o nível em jan/25; a piora desde então é real. E {_fmt(val('scr_ap'),1)}% do book já é 'problema'."),
    nota="Fonte: SCR.data/BCB, agregação própria dos arquivos abertos (bucket Empréstimos PF).")

# 13 ─ baixas trimestrais
g = com_janelas([rbarras_tri(D["ifd_baixas_tri"], H=350, title="Baixas para prejuízo — sistema bancário (R$ bi por trimestre)",
               sub="reconstrução: baixas = despesa de PDD − Δ provisão · IF.data · * 1T25 indefinido (adoção da 4.966)",
               destaque_ym="2026-06", nan_ym="2025-03")], lambda v: viz(v[0]))
sec("parte 3 · baixas e provisões", "A onda de baixas chegou: R$ 77 bi num trimestre.", g,
    verde=("Recorde nominal da série — 34% acima do trimestre anterior. Era a peça anunciada pela despesa de PDD.",
           "Baixa remove do numerador: daqui em diante ela segura o índice medido — sem melhorar o fluxo."),
    nota="Fonte: IF.data/BCB (conglomerados prudenciais), contas 78191/78192/78213 (2025+: 140205/140202/141840). Sistema total (PF+PJ).")

# 14 ─ baixas em % (carteira e NPL)
ga = rlinhas([
    {"pts": D["ifd_pdd_pct"], "cor": S2, "w": 2.2, "rot": "despesa PDD", "dec": 1},
    {"pts": D["ifd_baixas_pct"], "cor": S1, "w": 2.4, "rot": "baixas", "dec": 1},
], W=480, H=330, title="% da carteira (anualizado)", sub="custo do risco × limpeza do balanço", unit="%")
gb = rlinhas([
    {"pts": D["ifd_baixas_pct_npl"], "cor": S1, "w": 2.4, "rot": "baixas ÷ NPL", "dec": 0},
], W=480, H=330, title="Baixas ÷ NPL anterior (%)", sub="anualizado · quanto do estoque podre é limpo por ano", unit="%")
sec("parte 3 · baixas e provisões", "Formação bruta de ~5% da carteira ao ano.", com_janelas([ga, gb], lambda v: duo(viz(v[0]), viz(v[1]))),
    verde=("Mesmo baixando ~5% da carteira ao ano, o índice fez recorde — a formação de NPL cresceu ~40% num ano.",
           "O giro do estoque podre caiu de ~110% para ~88%/ano em 2025 — e a onda do 2T26 o devolveu a ~107%: a esteira reagiu."),
    nota="Baixas ÷ NPL usa inadimplência SFN (SGS 21082) sobre a carteira IF.data — aproximação; tendência sólida, nível indicativo.")

# 15 ─ provisão e cobertura
ga = rlinhas([{"pts": D["ifd_prov_pct"], "cor": S1, "w": 2.4, "rot": "provisão", "dec": 1}],
            W=480, H=330, title="Provisão em % da carteira", sub="estoque de PDD/perda esperada · IF.data", unit="%",
            ann=[{"ym": "2025-03", "v": em("ifd_prov_pct", "2025-03"), "t": "adoção 4.966", "dy": 3, "dx": -8, "anchor": "end"}])
gb = rlinhas([{"pts": D["ifd_cobertura"], "cor": S2, "w": 2.4, "rot": "cobertura", "dec": 0}],
            W=480, H=330, title="Cobertura (%)", sub="provisão ÷ NPL · colchão sobre o estoque em atraso", unit="%")
sec("parte 3 · baixas e provisões", "Provisão recorde — e a cobertura ainda cai.", com_janelas([ga, gb], lambda v: duo(viz(v[0]), viz(v[1]))),
    verde=("7,7% da carteira provisionada, máxima da série — e a cobertura caiu de ~180% para ~170%.",
           "Nem provisionamento recorde acompanha a formação. Este é o elo que devolve o calote ao spread."),
    nota="Fonte: IF.data/BCB. Salto de 1T25 na provisão = ajuste de adoção da Res. 4.966 (contra patrimônio).")

# 16 ─ comprometimento
g = jan1([
    {"pts": D["comprometimento"], "cor": S1, "w": 2.6, "rot": "serviço total", "dec": 1},
    {"pts": D["comp_amort"], "cor": MU, "rot": "amortização", "dec": 1},
    {"pts": D["comp_juros"], "cor": S2, "dash": "4 3", "rot": "juros", "dec": 1},
], title="Comprometimento de renda das famílias (% da renda mensal)", sub="SGS 29034 e decomposição oficial 29263/29264 · dado até jun/26",
    unit="%", H=385,
    ann=[{"ym": D["comprometimento"][-1][0], "v": comp, "t": f"recorde: {_fmt(comp,1)}%", "dy": -12, "anchor": "end", "cor": S1}])
sec("parte 4 · o tomador e o ciclo", "29% da renda já vai para a dívida.", g,
    verde=("Recorde da série — e a fatia de juros (10,8%) sozinha supera o serviço TOTAL das famílias americanas.",
           "Dois terços do serviço são amortização (principal rolável); o que não rola é o juro."),
    nota="Fonte: BCB/SGS (metodologia própria do BCB; sai com ~2 meses de defasagem).")

# 17 ─ atraso curto
g = jan1([
    {"pts": D["inad_pf_livre"], "cor": MU, "rot": "inad livre (>90d)", "dec": 2},
    {"pts": D["atraso_curto"], "cor": S1, "w": 2.6, "rot": "atraso 15-90d", "dec": 2},
], title="O antecedente: atraso curto PF 15-90 dias × inadimplência (%)", sub="SGS 21005 e 21112 · o atraso curto lidera a inad em ~3 meses (r=0,69)",
    unit="%", H=390,
    ann=[{"ym": "2026-06", "v": em("atraso_curto", "2026-06"), "t": "pico: 6,23 (jun)", "dy": -12, "cor": S1},
         {"ym": "2016-09", "v": em("atraso_curto", "2016-09"), "t": "máx da série: 6,77", "dy": -12}])
sec("parte 4 · o tomador e o ciclo", "O antecedente fez pico. A virada tem data provável.", g,
    verde=("Atraso curto: 6,23% em junho, 6,16% em julho — primeiro tique para baixo do ciclo.",
           "Se ago-set confirmarem, o pico do >90d fica para a virada 2026/27. É O indicador a vigiar dia 29/09."),
    nota="Correlação máxima entre Δ12m do atraso e Δ12m da inad livre com defasagem de 3 meses (ex-2020/21).")

# 18 ─ modelo × realizado
safra = D["proj_safras"][-1]
band_pts = [[p, v - b, v + b] for p, v, b in safra["pts"]]
g = linhas([
    {"pts": desde("inad_exagro", "2022-01"), "cor": S1, "w": 2.6, "rot": "realizado (ex-agro)", "dec": 2},
    {"pts": [[p, v] for p, v, _ in safra["pts"]], "cor": S2, "dash": "5 3", "rot": f"projeção (safra {safra['vintage']})", "dec": 2},
] + [{"pts": [[p, v] for p, v, _ in s["pts"]], "cor": "var(--grid)", "w": 1.4, "dash": "2 3"}
     for s in D["proj_safras"][:-1]],
    band={"pts": band_pts, "cor": S2},
    title="Projeção × realizado — inadimplência PF ex-agro (%)", sub="modelo de projeções diretas (G22): drivers macro + dummy 4.966 · banda de 80%",
    unit="%", H=405)
sec("parte 4 · o tomador e o ciclo", "O ciclo correu mais rápido que o modelo.", viz(g),
    verde=("10 de 16 verificações fora da banda, quase todas para cima — julho: projetado 4,94, realizado 5,40.",
           "O que os drivers macro não veem é composição de safra: Crédito do Trabalhador e agro."),
    nota="Safras registradas uma única vez por vintage (projecoes_hist.csv, commitado) — teste honesto, fora da amostra.")

# 19 ─ DSR ranking
NOME = {"HK": "Hong Kong", "BR": "Brasil", "NO": "Noruega", "CA": "Canadá", "SE": "Suécia", "KR": "Coreia",
        "AU": "Austrália", "NL": "Holanda", "US": "EUA", "CH": "Suíça", "FR": "França", "JP": "Japão",
        "CN": "China", "TR": "Turquia", "RU": "Rússia", "BE": "Bélgica", "FI": "Finlândia", "DK": "Dinamarca",
        "GB": "Reino Unido", "DE": "Alemanha", "ES": "Espanha", "PT": "Portugal", "IT": "Itália", "TH": "Tailândia",
        "MY": "Malásia", "SA": "Ar. Saudita", "IN": "Índia", "ID": "Indonésia", "MX": "México", "PL": "Polônia",
        "ZA": "Áfr. do Sul", "CZ": "Tchéquia", "HU": "Hungria", "GR": "Grécia", "IE": "Irlanda", "AT": "Áustria",
        "SG": "Singapura", "NZ": "N. Zelândia", "LU": "Luxemburgo", "IL": "Israel", "CL": "Chile", "CO": "Colômbia", "AR": "Argentina"}
rank = [(NOME.get(c, c), v, None) for c, v in D["dsr_rank"]]
g = barras_h(rank, title=f"Serviço da dívida do setor privado (% da renda) — {D['bis_tri']}",
             sub="DSR do BIS · mesma fórmula em 32 países · setor privado não financeiro", unit="%", dec=1, destaque="Brasil")
sec("parte 5 · o brasil no mundo", "O 2º maior serviço de dívida do planeta.", viz(g),
    verde=(f"{_fmt(dsr,1)}% da renda — atrás só de Hong Kong, à frente de Noruega, Canadá e Suécia.",
           "E subindo: 29,3% no 4T25 → 29,8% no 1T26."),
    nota="Fonte: BIS Debt Service Ratios (API SDMX). Brasil não entra no recorte só-famílias do BIS; o privado total entra.")

# 20 ─ quadrante deve pouco paga muito
dsr_map = dict(D["dsr_rank"])
pts = [(NOME.get(c, c), D["cred_gdp"].get(c), v, c == "BR")
       for c, v in dsr_map.items() if D["cred_gdp"].get(c)]
g = dispersao(pts, title="Deve pouco, paga muito — dívida × serviço", sub="vertical: serviço da dívida (% da renda) · cada ponto é um país · BIS, último trimestre disponível",
              xl="crédito ao setor privado (% do PIB)", abaixo=("Coreia", "Japão"))
sec("parte 5 · o brasil no mundo", "Deve pouco. Paga muito.", viz(g),
    verde=("Dívida entre as menores do mundo pagando serviço de topo: o peso é PREÇO (juros + prazo), não quantidade.",
           "Austrália e Holanda devem 2x mais e carregam mais barato. A razão custo/dívida do Brasil é ~3x a dos avançados."),
    nota="Fonte: BIS (WS_TC, crédito total ao setor privado não financeiro; WS_DSR). Famílias BR: dívida ~38% do PIB.")

# 21 ─ decomposição ICC
comp_icc = sorted(D["icc_decomp"]["comp"], key=lambda t: -t[1])
cores = {"Inadimplência": S1}
g = barras_h([(n, v, cores.get(n)) for n, v in comp_icc],
             title=f"De que é feito o custo do crédito (% do ICC) — BCB, {D['icc_decomp']['ref']}",
             sub="decomposição contábil do BCB (Relatório de Economia Bancária)", unit="%", dec=1, destaque="Inadimplência")
sec("parte 5 · o brasil no mundo", "O spread não é (só) lucro: é calote.", viz(g),
    verde=("Tirando a captação, a inadimplência é a maior fatia do custo — maior que o lucro do banco.",
           "O loop do deck inteiro: calote alto → spread alto → serviço mais caro → mais calote."),
    nota="Fonte: BCB/REB. Margem financeira é resíduo (inclui lucro e custo de capital); fatias mudam pouco entre edições.")

# 22 ─ síntese
teses = [
    ("1", "É piora real, não mix.", "Três shift-shares (renda, produto, banco) atribuem ~90-110% da alta à deterioração dentro dos grupos."),
    ("2", "Dois choques + um core caro.", "Agro (solvência) e consignado novo (safra) sobre um core em 5,3% — alto, mas ainda abaixo de 2012."),
    ("3", "O índice subestima o fluxo.", "Carteira crescendo dilui; baixas de R$ 77 bi/tri removem. Formação bruta ≈ 5% da carteira/ano."),
    ("4", "Deve pouco, paga muito.", "Dívida ~38% do PIB, serviço 2º maior do mundo (29,8%). O problema é preço, não quantidade."),
    ("5", "Calote → spread → calote.", "Inadimplência é a maior fatia do spread. Provisão recorde com cobertura em queda mantém o loop armado."),
]
cards = "".join(f'<div class="c3"><span class="c3n">{n}</span><b>{t}</b> {d}</div>' for n, t, d in teses)
corpo = f'<div class="cards3" style="grid-template-columns:repeat(3,1fr)">{cards[:0]}</div>'
corpo = f'<div class="cards3">{cards}</div>'
sec("síntese · as 5 teses", "O que os dados sustentam.", corpo,
    verde=("Preço recorde, dois choques de safra e a onda de baixas em curso — o pico do índice fica para a virada 2026/27, se o antecedente confirmar.",
           f"Próxima nota do BCB: ~29/09 (competência ago/26). Dashboard vivo: dashboard-bcb · v{VERSAO} · {HOJE}"))

# ── template ──────────────────────────────────────────────────────────────────
TPL = open(RAIZ / "_template.html", encoding="utf-8").read()
html = (TPL.replace("%%SLIDES%%", "\n".join(SLIDES))
           .replace("%%CHIP%%", f"v{VERSAO} · {HOJE} · dados até jul/26 · {len(SLIDES)} slides"))
open(RAIZ / "index.html", "w", encoding="utf-8").write(html)
print(f"OK: index.html com {len(SLIDES)} slides")
