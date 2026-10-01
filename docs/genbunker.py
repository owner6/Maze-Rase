"""Комбінована карта бункера: кімнати, вентиляція, потоки повітря, температура і CO₂ на одному аркуші.

Складається з наявних прототипів (той самий seed → та сама карта):
  • genmap.py   — лабіринт, кімнати, регіони Вороного (REQ-MAZE-03…05)
  • genvent.py  — граф вентиляції: серце, магістраль, камери, решітки, зворотний потік, застійні зони (REQ-VENT-01…03, 11)
  • gentemp.py  — температура повітря через T_MIN хв за сіткою дифузії (REQ-VENT-07, roadmap REQ-CLIMATE-07)
  • гази за genair.py — по повітряних зонах: зачинені кімнати, застійні підзони, зони гілок; CO₂, O₂, CO печі (REQ-VENT-14, roadmap REQ-VENT-24, DEC-068…071)

Запуск: python genbunker.py <seed> <off|generator|pump|boiler> [хвилин=240] [--stove] [--outside=T] [--recirc=R]
Результат: docs/bunker_seed<seed>_<стан>.png
"""
import sys, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch, Rectangle, FancyBboxPatch
import numpy as np

here = os.path.dirname(os.path.abspath(__file__))
argv = [a for a in sys.argv if not a.startswith("--")]
if len(argv) < 4:
    argv = argv[:3] + ["240"]
sys.argv = argv + [a for a in sys.argv if a.startswith("--")]

# --- 1. Уся модель до малюнка gentemp.py (карта → вентиляція → температура → потоки) ---
src = open(os.path.join(here, "gentemp.py"), encoding="utf-8").read().split("# --- 5. Малюнок ---")[0]
# Подача за ТАБЛИЦЕЮ РЕЖИМІВ специфікації (REQ-VENT-07, DEC-014): калорифер у MVP працює в обидва боки,
# тому з насосом Морозильна отримує −30, а не +9, як у gentemp.py (той лише гріє — розбіжність зафіксована в DEC-014).
OLD_RULE = (
    '    if STATE == "off": return T_heart\n'
    '    if STATE == "generator": return max(T_heart, min(setpoint[branch], max(T_heart, 15.0))) if branch == gen_region else T_heart\n'
    '    if STATE == "pump": return max(T_heart, min(setpoint[branch], max(T_heart, 15.0)))\n'
    '    return max(T_heart, setpoint[branch])')
NEW_RULE = (
    '    if STATE == "off": return T_heart\n'
    '    if STATE == "generator": return min(setpoint[branch], 15.0) if branch == gen_region else T_heart\n'
    '    if STATE == "pump": return min(setpoint[branch], 15.0)\n'
    '    return setpoint[branch]')
assert OLD_RULE in src, "gentemp.py змінився: правило подачі не знайдено"
src = src.replace(OLD_RULE, NEW_RULE)
g = {"__name__": "gentemp", "sys": sys, "__file__": os.path.join(here, "gentemp.py")}
exec(src, g)
N, maze, rooms, climate, PATH = g["N"], g["maze"], g["rooms"], g["climate"], g["PATH"]
gv, gm = g["g"], g["gm"]
start, exit_, SEED, STATE = g["start"], g["exit_"], g["SEED"], g["STATE"]
grilles, chambers, ret_next, stagnant = g["grilles"], g["chambers"], g["ret_next"], g["stagnant"]
Ta, supply, flow, FLOW, T_MIN = g["Ta"], g["supply"], g["flow"], g["FLOW"], g["T_MIN"]
OUTSIDE, RECIRC, stove_cell, sources = g["OUTSIDE"], g["RECIRC"], g["stove_cell"], g["sources"]
BRANCH_COLORS, CLIMATES, PALETTE_ = g["BRANCH_COLORS"], g["CLIMATES"], g["PALETTE_"]
gen, branch_edges, serve, npcs = gv["gen"], gv["branch_edges"], gv["serve"], gv["npcs"]
path_cells = g["path_cells"]
BRANCH_NAMES = "12345"

# --- 2. Гази по повітряних зонах (REQ-VENT-09/11/12/14, roadmap REQ-VENT-24; DEC-068…071) ---
#   4 людини в кожній з трьох спалень і гравець у боксі за зачиненими дверима (зона = кімната, обмін через щілину 8 м³/год);
#   застійні тупики — підзони з межею 15 м³/год на клітинку; решта проходів — одна зона на гілку з Q = решітки × 6 × свіжий потік.
#   Усі джерела фізичні, крок dt = AIR_SPEEDUP/60 год за ігрову хвилину (DEC-069). Буржуйка (--stove) стоїть у першій спальні:
#   без димоходу дає CO 0,03 м³/год (× 3 при O₂ < 19 %), CO₂ 0,9 і O₂ −0,9 м³/год; гасне при O₂ < 16 %.
import math
AIR_SPEEDUP, DT, V_CELL = 12, 12 / 60.0, 51.0
G_PERSON, Q_GRILLE, Q_SLIT, Q_STAG, C_OUT = 0.02, 6.0, 8.0, 15.0, 0.04
bedrooms = [(r0, c0, h, w) for r0, c0, h, w, t in rooms if t == "Спальня"][:3]
zones, zone_of, zid, closed = {}, {}, 0, set()
for (r0, c0, h, w) in bedrooms:
    cc = [(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)]
    zones[zid] = (cc, 4); closed.add(zid)
    for c in cc: zone_of[c] = zid
    zid += 1
zones[zid] = ([start], 1); zone_of[start] = zid; closed.add(zid); zid += 1
stag_zones = set()
STAG = set(stagnant) - set(zone_of)
seen = set()
for p in sorted(STAG):
    if p in seen: continue
    comp, stack = [], [p]; seen.add(p)
    while stack:
        q = stack.pop(); comp.append(q)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (q[0] + dr, q[1] + dc)
            if n in STAG and n not in seen: seen.add(n); stack.append(n)
    zones[zid] = (comp, 0); stag_zones.add(zid)
    for c in comp: zone_of[c] = zid
    zid += 1
open_zones = {}
for p in path_cells:
    if p in zone_of: continue
    open_zones.setdefault(serve.get(p, 0), []).append(p)
for b, cc in open_zones.items():
    zones[zid] = (cc, 0)
    for c in cc: zone_of[c] = zid
    zid += 1
neigh = collections.defaultdict(set)                       # зачинена кімната -> сусідні зони (одні двері на зону)
border = collections.defaultdict(collections.Counter)      # застійна підзона -> {зона: клітинок межі}
for z in list(closed) + list(stag_zones):
    for (r, c) in zones[z][0]:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if n in zone_of and zone_of[n] != z:
                if z in closed: neigh[z].add(zone_of[n])
                elif zone_of[n] not in stag_zones: border[z][zone_of[n]] += 1
grilles_in_zone = collections.Counter(zone_of[p] for p in grilles if p in zone_of)
stove_zone = zone_of[stove_cell] if stove_cell else None

fresh_flow = FLOW * 100 * (1 - RECIRC)                     # свіжий потік 0…100 за станом установки
vol = {z: len(cc) * V_CELL for z, (cc, _) in zones.items()}
Q = {z: (grilles_in_zone.get(z, 0) * Q_GRILLE * fresh_flow if (z not in closed and z not in stag_zones) else 0.0) for z in zones}
co2 = {z: C_OUT for z in zones}; co = {z: 0.0 for z in zones}; o2burn = {z: 0.0 for z in zones}
stove_on = bool(stove_cell); stove_out_min = None
def o2_of(z): return 20.9 - 1.1 * (co2[z] - C_OUT) - o2burn[z]
def step_gas(c, gsrc, q, z, cin):
    if q > 0:
        ceq = cin + 100.0 * gsrc / q
        return ceq + (c - ceq) * math.exp(-q * DT / vol[z])
    return c + 100.0 * gsrc * DT / vol[z]
for t in range(T_MIN):
    qsum = sum(Q[z] for z in zones if Q[z] > 0)
    c_ret = sum(co2[z] * Q[z] for z in zones if Q[z] > 0) / qsum if qsum > 0 else C_OUT
    cin = C_OUT + RECIRC * (c_ret - C_OUT)
    n2, nco = dict(co2), dict(co)
    for z, (cc, ppl) in zones.items():
        gsrc = ppl * G_PERSON
        gco = 0.0
        if stove_on and z == stove_zone:
            gsrc += 0.9
            gco = 0.03 * (3.0 if o2_of(z) < 19.0 else 1.0)
        n2[z] = step_gas(co2[z], gsrc, Q[z], z, cin)
        nco[z] = step_gas(co[z] * 30.0, gco * 1e4, Q[z], z, 0.0) / 30.0   # ppm ↔ од. (1 од. = 30 ppm); G у м³/год → ppm через ×1e6/100
    for z in closed:
        for nz in neigh[z]:
            for arr in (n2, nco):
                base = co2 if arr is n2 else co
                flux = Q_SLIT * DT * (base[z] - base[nz]); arr[z] -= flux / vol[z]; arr[nz] += flux / vol[nz]
    for z in stag_zones:
        for nz, nb in border[z].items():
            for arr in (n2, nco):
                base = co2 if arr is n2 else co
                flux = Q_STAG * nb * DT * (base[z] - base[nz]); arr[z] -= flux / vol[z]; arr[nz] += flux / vol[nz]
    co2 = {z: max(C_OUT, min(100.0, v)) for z, v in n2.items()}
    co = {z: max(0.0, min(100.0, v)) for z, v in nco.items()}
    if stove_on and o2_of(stove_zone) < 16.0:
        stove_on = False; stove_out_min = t
def eta_to3(z):
    ppl = zones[z][1]; gsrc = ppl * G_PERSON + (0.9 if (stove_on and z == stove_zone) else 0.0)
    if gsrc <= 0 or co2[z] >= 3: return None if gsrc <= 0 else 0.0
    if z in closed:
        q = Q_SLIT * len(neigh[z]); cin = sum(co2[n] for n in neigh[z]) / max(1, len(neigh[z]))
    elif z in stag_zones:
        q = Q_STAG * sum(border[z].values()); cin = C_OUT
    else:
        q, cin = Q[z], C_OUT
    if q <= 0: return (3 - co2[z]) * vol[z] / (100 * gsrc) / AIR_SPEEDUP
    ceq = cin + 100 * gsrc / q
    return None if ceq <= 3 else -(vol[z] / q) * math.log((ceq - 3) / (ceq - co2[z])) / AIR_SPEEDUP

# --- 3. Малюнок ---
X = lambda c: c + 0.5
Y = lambda r: N - 1 - r + 0.5
fig = plt.figure(figsize=(26, 15.5))
gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1], wspace=0.03)
ax = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])
tcmap, tnorm = plt.get_cmap("coolwarm"), mcolors.Normalize(vmin=-30, vmax=58)
ccmap, cnorm = plt.get_cmap("YlOrRd"), mcolors.Normalize(vmin=0, vmax=8)
fmax = max(flow.values()) if flow else 1

for r in range(N):
    for c in range(N):
        if maze[r][c] != PATH:
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color="#2c3e50"))
            ax2.add_patch(Rectangle((c, N - 1 - r), 1, 1, color="#2c3e50"))
        else:
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=tcmap(tnorm(Ta[(r, c)]))))
            ax2.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=ccmap(cnorm(co2[zone_of[(r, c)]]))))
# застійні зони
for p in stagnant:
    for a in (ax, ax2):
        a.add_patch(Rectangle((p[1], N - 1 - p[0]), 1, 1, facecolor="none", hatch="////", edgecolor="#444", lw=0))
# ізотерми смуг 12.1
Z = np.full((N, N), np.nan)
for (r, c), t in Ta.items(): Z[r, c] = t
ax.contour(np.arange(N) + 0.5, N - 1 - np.arange(N) + 0.5, np.ma.masked_invalid(Z), levels=[-5, 12, 24, 30],
           colors="k", linewidths=0.6, alpha=0.55, corner_mask=True)
# межі регіонів
for r in range(N):
    for c in range(N):
        if c + 1 < N and climate[r][c] != climate[r][c + 1]:
            ax.plot([c + 1, c + 1], [N - 1 - r, N - r], color="#222", lw=0.9, ls=(0, (2, 2)), zorder=2)
        if r + 1 < N and climate[r][c] != climate[r + 1][c]:
            ax.plot([c, c + 1], [N - 1 - r, N - 1 - r], color="#222", lw=0.9, ls=(0, (2, 2)), zorder=2)
# зворотний потік повітря проходами до камери: товщина і колір за накопиченим потоком
fcmap, fnorm = plt.get_cmap("viridis"), mcolors.LogNorm(vmin=1, vmax=fmax)
for (r, c), (pr, pc) in ret_next.items():
    f = flow.get((r, c), 1)
    if f < 3 and (r + c) % 2: continue                          # проріджуємо дрібні
    col = fcmap(fnorm(max(f, 1)))
    dr, dc = pr - r, pc - c
    s = (f / fmax) ** 0.5
    ax.arrow(X(c), Y(r), dc * 0.45, -dr * 0.45, width=0.02 + 0.09 * s, head_width=0.2 + 0.22 * s,
             head_length=0.18, length_includes_head=True, color=col, alpha=0.9, zorder=3)
# труби: магістраль (витяжний ствол + нагнітальний канал) і гілки (MST до решіток)
def L(a, b, **kw):
    ax.plot([X(a[1]), X(b[1]), X(b[1])], [Y(a[0]), Y(a[0]), Y(b[0])], solid_capstyle="round", **kw)
for ch in chambers:
    L(gen, ch, color="#7f8c8d", lw=7, alpha=0.95, zorder=4)
    L(gen, ch, color="white", lw=2.0, ls=(0, (1.5, 1.5)), zorder=5)
for i, edges in enumerate(branch_edges):
    for a, b in edges:
        L(a, b, color=BRANCH_COLORS[i], lw=2.0, alpha=0.95, zorder=6)
# кімнати з назвою і середньою температурою
for r0, c0, h, w, t in rooms:
    tavg = sum(Ta[(r, c)] for r in range(r0, r0 + h) for c in range(c0, c0 + w)) / (h * w)
    for a in (ax, ax2):
        a.add_patch(Rectangle((c0, N - r0 - h), w, h, facecolor="none", edgecolor="black", lw=1.6, zorder=7))
    ax.text(c0 + w / 2, N - r0 - h / 2, f"{t}\n{tavg:+.0f}°", ha="center", va="center", fontsize=6.2, weight="bold", zorder=9,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.75))
# решітки, камери, серце, шахта
for p, (b, kind) in grilles.items():
    ms = 9 if kind == "spawn" else 7 if kind == "room" else 5.5
    ax.plot(X(p[1]), Y(p[0]), "s", ms=ms, color=BRANCH_COLORS[b], mec="#c0392b" if kind == "spawn" else "black",
            mew=2 if kind == "spawn" else 0.8, zorder=8)
    ax2.plot(X(p[1]), Y(p[0]), "s", ms=4, color="white", mec="black", mew=0.6, zorder=8)
for i, ch in enumerate(chambers):
    ax.plot(X(ch[1]), Y(ch[0]), "D", ms=16, color=BRANCH_COLORS[i], mec="black", mew=1.5, zorder=9)
    ax.text(X(ch[1]), Y(ch[0]), BRANCH_NAMES[i], ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=10)
ax.plot(X(gen[1]), Y(gen[0]), "o", ms=20, color="#d35400", mec="black", mew=2, zorder=9)
ax.text(X(gen[1]), Y(gen[0]), "♥", ha="center", va="center", fontsize=11, color="white", zorder=10)
sx, sy = X(gen[1]), Y(gen[0])
ax.annotate("", xy=(sx - 0.45, sy + 4.2), xytext=(sx - 0.45, sy + 1.2), arrowprops=dict(arrowstyle="-|>", color="#e74c3c", lw=3), zorder=10)
ax.annotate("", xy=(sx + 0.45, sy + 1.2), xytext=(sx + 0.45, sy + 4.2), arrowprops=dict(arrowstyle="-|>", color="#2980b9", lw=3), zorder=10)
ax.text(sx - 0.9, sy + 2.7, "ВИКИД", ha="right", va="center", fontsize=7.5, weight="bold", color="#e74c3c", zorder=10,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e74c3c", lw=0.8))
ax.text(sx + 0.9, sy + 2.7, f"ПРИПЛИВ {OUTSIDE:+.0f}°", ha="left", va="center", fontsize=7.5, weight="bold", color="#2980b9", zorder=10,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#2980b9", lw=0.8))
if stove_cell:
    ax.plot(X(stove_cell[1]), Y(stove_cell[0]), "*", ms=18, color="#f39c12", mec="black", zorder=10)
for a in (ax, ax2):
    a.add_patch(Rectangle((start[1], N - 1 - start[0]), 1, 1, color="#2ecc71", ec="black", lw=2, zorder=8))
    a.text(X(start[1]), Y(start[0]), "S", ha="center", va="center", fontsize=8, weight="bold", zorder=11)
    a.add_patch(Rectangle((exit_[1], N - 1 - exit_[0]), 1, 1, color="#e74c3c", ec="black", lw=2, zorder=8))
    a.text(X(exit_[1]), Y(exit_[0]), "E", ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=11)
    a.set_xlim(0, N); a.set_ylim(0, N); a.set_aspect("equal"); a.axis("off")
for r, c in npcs:
    ax.plot(X(c), Y(r), "^", color="#2980b9", ms=11, mec="black", zorder=9)
# гази: підписи на зонах з людьми, з піччю і на застійних підзонах
def fmt_eta(e): return "∞" if e is None else (f"{e:.0f} год" if e >= 1 else f"{e*60:.0f} хв")
for z, (cc, ppl) in zones.items():
    if not ppl and z != stove_zone: continue
    rs = [p[0] for p in cc]; cs = [p[1] for p in cc]
    txt = (f"{ppl} люд." if ppl else "піч") + f"\nCO₂ {co2[z]:.2f} %  O₂ {o2_of(z):.1f} %"
    if z == stove_zone: txt += f"\nCO {co[z]:.0f} од." + (" · піч згасла" if not stove_on else "")
    e = eta_to3(z)
    if e is not None: txt += f"\n3 % через {fmt_eta(e)}"
    elif co2[z] >= 1.5: txt += "\nважке повітря"
    ax2.text((min(cs) + max(cs) + 1) / 2, N - 1 - (min(rs) + max(rs)) / 2 + 0.5, txt,
             ha="center", va="center", fontsize=7, weight="bold", zorder=10,
             bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.9, lw=0.5))
for z in stag_zones:
    for (r, c) in zones[z][0]:
        ax2.add_patch(Rectangle((c, N - 1 - r), 1, 1, facecolor="none", hatch="////", edgecolor="#444", lw=0, zorder=6))

# --- заголовки, шкали, легенда ---
sup_str = "; ".join(f"гілка {i+1} {PALETTE_[i][0]} → подача {g['supply_of'](i, (1 - RECIRC) * OUTSIDE + RECIRC * 9.0):+.0f}°" for i in range(5))
temps = sorted(Ta.values())
ax.set_title(f"Сектор 45×45, seed {SEED} — стан установки «{STATE}», потік {int(FLOW*100)}, зовні {OUTSIDE:+.0f}°, "
             f"рециркуляція {int(RECIRC*100)} %, через {T_MIN} ігр. хв\n{sup_str}\n"
             f"температура повітря: min {temps[0]:+.0f}° · медіана {temps[len(temps)//2]:+.0f}° · max {temps[-1]:+.0f}°; "
             f"{len(grilles)} решіток, {len(stagnant)} застійних клітинок",
             fontsize=10.5, linespacing=1.45)
worst = max(co2[z] for z, (cc, ppl) in zones.items() if ppl or z == stove_zone)
o2min = min(o2_of(z) for z, (cc, ppl) in zones.items() if ppl or z == stove_zone)
ax2.set_title(f"Гази по зонах, той самий стан установки: свіжий потік {fresh_flow:.0f}, AIR_SPEEDUP {AIR_SPEEDUP}, {T_MIN} ігр. хв\n"
              f"12 NPC у 3 спальнях і гравець у боксі за зачиненими дверима (щілина 8), {len(stag_zones)} застійних підзон (межа 15 м³/год)\n"
              f"CO₂ до {worst:.2f} %, O₂ не нижче {o2min:.1f} %"
              + (f"; буржуйка у спальні: CO {co[stove_zone]:.0f} од." + (f", згасла на {stove_out_min}-й хв" if stove_out_min is not None else "") if stove_cell else "")
              + "\nпороги CO₂ 1,5 / 3 / 5 / 8 %; CO 30 / 60 / 90 од. (REQ-VENT-14, REQ-VENT-24)",
              fontsize=10, linespacing=1.4)
st = plt.cm.ScalarMappable(cmap=tcmap, norm=tnorm); st.set_array([])
fig.colorbar(st, ax=ax, fraction=0.03, pad=0.005, label="T повітря, °C (ізотерми −5 / 12 / 24 / 30 — смуги HUD)")
sc = plt.cm.ScalarMappable(cmap=ccmap, norm=cnorm); sc.set_array([])
fig.colorbar(sc, ax=ax2, fraction=0.03, pad=0.005, label="CO₂ зони, % об.")
sf = plt.cm.ScalarMappable(cmap=fcmap, norm=fnorm); sf.set_array([])
fig.colorbar(sf, ax=ax, fraction=0.03, pad=0.02, orientation="horizontal", label="зворотний потік повітря проходами до камери: накопичено клітинок")
legend = [Patch(color="#2c3e50", label="Стіна (панель на рейці)"),
          plt.Line2D([], [], color="#7f8c8d", lw=6, label="Магістраль: витяжний ствол (лаз) + нагнітальний канал + стояк"),
          plt.Line2D([], [], color="#333", lw=2, label="Труба гілки — приплив до решіток"),
          plt.Line2D([], [], marker="D", color="#888", ms=11, ls="", mec="black", label="Камера гілки: витяг + заслінка + калорифер"),
          plt.Line2D([], [], marker="o", color="#d35400", ms=12, ls="", mec="black", label="Генераторна «серце» + вентшахта на поверхню"),
          plt.Line2D([], [], marker="s", color="#aaa", ms=7, ls="", mec="black", label="Решітка припливна (кімната / коридор)"),
          plt.Line2D([], [], marker="s", color="#aaa", ms=8, ls="", mec="#c0392b", mew=2, label="Решітка-спавн заражених"),
          plt.Line2D([], [], color="#2a788e", lw=2, label="Зворотний потік (двері + коридори → камера)"),
          Patch(facecolor="none", hatch="////", edgecolor="#444", label="Застійна зона (статична від seed)"),
          plt.Line2D([], [], color="#222", lw=1, ls=(0, (2, 2)), label="Межа кліматичного регіону"),
          plt.Line2D([], [], marker="^", color="#2980b9", ls="", mec="black", label="NPC"),
          Patch(color="#2ecc71", label="Старт"), Patch(color="#e74c3c", label="Шлюз")]
if stove_cell:
    legend.append(plt.Line2D([], [], marker="*", color="#f39c12", ms=12, ls="", mec="black", label="Буржуйка 4 кВт"))
fig.legend(handles=legend, loc="lower center", ncol=5, fontsize=8.5, frameon=False, bbox_to_anchor=(0.5, 0.005))
fig.suptitle("Карта бункера «Об’єкт 71»: кімнати, вентиляція, потоки повітря, температура, CO₂", fontsize=15, y=0.995)
fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.11)
tag = ("" if OUTSIDE == 9.0 else f"_out{int(OUTSIDE)}") + ("" if RECIRC == 0 else f"_R{int(RECIRC*100)}") + ("_stove" if stove_cell else "")
out = os.path.join(here, f"bunker_seed{SEED}_{STATE}{tag}.png")
plt.savefig(out, dpi=100)
print(out)
