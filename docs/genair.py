"""Карта повітря: CO₂ і кисень по повітряних зонах у чотирьох режимах ФВУ (REQ-VENT-14, REQ-VENT-21…24, DEC-068/069).

Модель (docs/spec/02-spec-mvp.md, означення «Модель газів»):
  • карта і вентиляція — genmap.py + genvent.py (той самий seed);
  • люди: 12 NPC по 4 у трьох спальнях за ЗАЧИНЕНИМИ дверима, гравець у стартовому боксі за зачиненими дверима;
  • повітряні зони: кожна зачинена кімната з людьми — окрема зона; решта сектора — одна зона на гілку (заливка від решіток);
  • усі величини фізичні: V = клітинки × 51 м³; людина 0,02 м³/год CO₂; решітка 6 м³/год на одиницю свіжого потоку;
    щілина зачинених дверей 8 м³/год; C_вх = 0,04 % + R × CO₂ витягу;
  • крок: C_рівн = C_вх + G/Q, C ← C_рівн + (C − C_рівн)·exp(−Q·dt/V); при Q = 0 — C += G·dt/V;
    dt = AIR_SPEEDUP/60 = 0,2 год за ігрову хвилину (єдина умовність моделі);
  • зачинена кімната не має зворотного шляху, тому Q її решітки = 0: свіже повітря лише через щілину;
  • O₂ = 20,9 − 1,1 × (CO₂ − 0,04); стани: heavy при CO₂ ≥ 1,5 % (назад при 1,2), countdown при C_рівн ≥ 3 % або Q = 0.
Режими: vent (генератор, потік 100), draft (тяга 10 при поверхні +9), isolation (шибер 0), recirc80 (генератор, R = 0,8).

Запуск: python genair.py 2031 [ігрових хвилин=360]
"""
import sys, os, collections, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch, Rectangle

here = os.path.dirname(os.path.abspath(__file__))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2031
T_MIN = int(sys.argv[2]) if len(sys.argv) > 2 else 360
sys.argv = [sys.argv[0], str(SEED), "off"]
src = open(os.path.join(here, "genvent.py"), encoding="utf-8").read().split("# --- 7. Малюнок ---")[0]
g = {"__name__": "genvent", "sys": sys, "__file__": os.path.join(here, "genvent.py")}
exec(src, g)
N, maze, rooms, PATH = g["N"], g["maze"], g["rooms"], g["PATH"]
start, exit_, grilles, serve = g["start"], g["exit_"], g["grilles"], g["serve"]
BRANCH_COLORS = g["BRANCH_COLORS"]
cells = [(r, c) for r in range(N) for c in range(N) if maze[r][c] == PATH]

# --- люди і зачинені кімнати ---
bedrooms = [(r0, c0, h, w) for r0, c0, h, w, t in rooms if t == "Спальня"][:3]
closed = {}   # zone id -> (cells, people)
zone_of = {}
zid = 0
for (r0, c0, h, w) in bedrooms:
    cc = [(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)]
    closed[zid] = (cc, 4)
    for c in cc: zone_of[c] = zid
    zid += 1
closed[zid] = ([start], 1); zone_of[start] = zid; zid += 1          # гравець у боксі
# застійні підзони (REQ-VENT-11, DEC-071): зв'язні множини застійних клітинок, обмін через межу q_заст
STAG = set(g["STAGNANT_FROZEN"]) - set(zone_of)
stag_zones = {}
seen = set()
for p in sorted(STAG):
    if p in seen: continue
    comp, stack = [], [p]; seen.add(p)
    while stack:
        q = stack.pop(); comp.append(q)
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (q[0]+dr, q[1]+dc)
            if n in STAG and n not in seen: seen.add(n); stack.append(n)
    stag_zones[zid] = (comp, 0)
    for c in comp: zone_of[c] = zid
    zid += 1
# решта: зона на гілку
open_zones = {}
for p in cells:
    if p in zone_of: continue
    b = serve.get(p, 0)
    open_zones.setdefault(b, []).append(p)
zones = dict(closed); zones.update(stag_zones)
for b, cc in open_zones.items():
    zones[zid] = (cc, 0)
    for c in cc: zone_of[c] = zid
    zid += 1
branch_of_zone = {z: (serve.get(cc[0], 0)) for z, (cc, _) in zones.items()}
# сусідство зачинених кімнат із зовнішньою зоною (щілина) і застійних підзон із коридором (межа)
neigh = collections.defaultdict(set)          # зачинені кімнати: множина сусідніх зон, по одних дверях на зону
border = collections.defaultdict(collections.Counter)   # застійні підзони: зона -> число клітинок межі
for z, (cc, _) in list(closed.items()) + list(stag_zones.items()):
    for (r, c) in cc:
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (r+dr, c+dc)
            if n in zone_of and zone_of[n] != z:
                if z in closed: neigh[z].add(zone_of[n])
                elif zone_of[n] not in stag_zones: border[z][zone_of[n]] += 1

AIR_SPEEDUP = 12
DT = AIR_SPEEDUP / 60.0          # год повітря за ігрову хвилину
V_CELL = 51.0                    # м³
G_PERSON = 0.02                  # м³/год CO₂ на людину в спокої
Q_GRILLE = 6.0                   # м³/год на одиницю свіжого потоку
Q_SLIT = 8.0                     # м³/год через зачинені двері без різниці тиску
Q_STAG = 15.0                    # м³/год на клітинку межі застійної підзони
C_OUT = 0.04                     # % CO₂ зовні
C_HEAVY, C_HEAVY_OFF, C_COUNT = 1.5, 1.2, 3.0

grilles_in_zone = collections.Counter(zone_of[p] for p in grilles if p in zone_of)

REGIMES = {"vent": (1.0, 1.0, 0.0), "draft": (1.0, 0.10, 0.0), "isolation": (0.0, 1.0, 0.0), "recirc80": (1.0, 1.0, 0.8)}
LABEL = {"vent": "Вентиляція: генератор, потік 100", "draft": "Природна тяга: без живлення, потік 10",
         "isolation": "Ізоляція: шибер 0", "recirc80": "Рециркуляція 80 %: генератор, свіжий потік 20"}

def o2_of(c): return 20.9 - 1.1 * (c - C_OUT)

def time_to(c, ceq, q, v, g, thr=C_COUNT):
    """Ігрові години до порога thr при сталих G і Q; None = ніколи."""
    if c >= thr: return 0.0
    if q <= 0:
        return None if g <= 0 else (thr - c) * v / (100.0 * g) / AIR_SPEEDUP
    if ceq <= thr: return None
    return -(v / q) * math.log((ceq - thr) / (ceq - c)) / AIR_SPEEDUP

def simulate(regime, minutes=None):
    minutes = T_MIN if minutes is None else minutes
    shiber, flow, R = REGIMES[regime]
    fresh = shiber * flow * 100 * (1 - R)                     # свіжий потік 0…100
    vol = {z: len(cc) * V_CELL for z, (cc, _) in zones.items()}
    people = {z: ppl for z, (cc, ppl) in zones.items()}
    Q = {z: (grilles_in_zone.get(z, 0) * Q_GRILLE * fresh if (z not in closed and z not in stag_zones) else 0.0) for z in zones}
    c = {z: C_OUT for z in zones}
    heavy = {z: False for z in zones}
    for t in range(minutes):
        # CO₂ витягу: середнє по відкритих зонах, зважене за Q
        qsum = sum(Q[z] for z in zones if Q[z] > 0)
        c_ret = sum(c[z] * Q[z] for z in zones if Q[z] > 0) / qsum if qsum > 0 else C_OUT
        c_in = C_OUT + R * (c_ret - C_OUT)
        new = dict(c)
        for z in zones:
            g = people[z] * G_PERSON
            if Q[z] > 0:
                ceq = c_in + 100.0 * g / Q[z]                 # % : G/Q — частка, ×100
                new[z] = ceq + (c[z] - ceq) * math.exp(-Q[z] * DT / vol[z])
            else:
                new[z] = c[z] + 100.0 * g * DT / vol[z]
        # щілини зачинених кімнат (маса зберігається)
        for z in closed:
            for nz in neigh.get(z, ()):
                flux = Q_SLIT * DT * (c[z] - c[nz])           # % · м³
                new[z] -= flux / vol[z]
                new[nz] += flux / vol[nz]
        # межі застійних підзон (маса зберігається)
        for z in stag_zones:
            for nz, nb in border[z].items():
                flux = Q_STAG * nb * DT * (c[z] - c[nz])
                new[z] -= flux / vol[z]
                new[nz] += flux / vol[nz]
        c = {z: max(C_OUT, min(100.0, v)) for z, v in new.items()}
        for z in zones:
            if c[z] >= C_HEAVY: heavy[z] = True
            elif c[z] <= C_HEAVY_OFF: heavy[z] = False
    # стани і час до 3 %
    state, eta = {}, {}
    for z in zones:
        g = people[z] * G_PERSON
        ceq = (C_OUT + 100.0 * g / Q[z]) if Q[z] > 0 else float("inf")
        if people[z] == 0: state[z] = "-"; eta[z] = None; continue
        if ceq >= C_COUNT or Q[z] <= 0:
            # у зачиненій кімнаті приплив лише через щілину: ефективна Q = щілини, C_вх ≈ CO₂ сусіда
            qeff = Q_SLIT * len(neigh.get(z, ())) if z in closed else Q[z]
            cin = (sum(c[nz] for nz in neigh[z]) / len(neigh[z])) if (z in closed and neigh[z]) else C_OUT
            ceq_eff = cin + 100.0 * g / qeff if qeff > 0 else float("inf")
            eta[z] = time_to(c[z], ceq_eff, qeff, vol[z], g)
            state[z] = "countdown" if (eta[z] is not None) else ("heavy" if heavy[z] else "norm")
        else:
            eta[z] = None
            state[z] = "heavy" if heavy[z] else "norm"
    return c, {z: o2_of(v) for z, v in c.items()}, fresh, state, eta

fig, axes = plt.subplots(2, 2, figsize=(20, 20))
cmap, norm = plt.get_cmap("YlOrRd"), mcolors.Normalize(vmin=0, vmax=8)
def fmt_eta(e): return "∞" if e is None else (f"{e:.0f} год" if e >= 1 else f"{e*60:.0f} хв")
for ax, regime in zip(axes.flat, REGIMES):
    co2, o2, fresh, state, eta = simulate(regime)
    for r in range(N):
        for c in range(N):
            if maze[r][c] != PATH:
                ax.add_patch(Rectangle((c, N-1-r), 1, 1, color="#2c3e50"))
            else:
                z = zone_of[(r, c)]
                ax.add_patch(Rectangle((c, N-1-r), 1, 1, color=cmap(norm(co2[z]))))
    for z, (cc, people) in zones.items():
        if not people: continue
        rs = [p[0] for p in cc]; cs = [p[1] for p in cc]
        ax.add_patch(Rectangle((min(cs), N-1-max(rs)), max(cs)-min(cs)+1, max(rs)-min(rs)+1, facecolor="none", edgecolor="black", lw=2))
        txt = f"{people} люд.\nCO₂ {co2[z]:.2f} %\nO₂ {o2[z]:.1f} %"
        if state[z] == "countdown": txt += f"\n3 % через {fmt_eta(eta[z])}"
        elif state[z] == "heavy": txt += "\nважке повітря"
        ax.text((min(cs)+max(cs)+1)/2, N-1-(min(rs)+max(rs))/2 + 0.5, txt, ha="center", va="center", fontsize=7, weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.85, lw=0.5))
    for p, (b, kind) in grilles.items():
        ax.plot(p[1]+0.5, N-1-p[0]+0.5, "s", ms=4, color="white", mec="black", mew=0.6)
    ax.set_xlim(0, N); ax.set_ylim(0, N); ax.set_aspect("equal"); ax.axis("off")
    worst = max((co2[z] for z, (cc, ppl) in zones.items() if ppl), default=0)
    o2min = min((o2[z] for z, (cc, ppl) in zones.items() if ppl), default=20.9)
    ax.set_title(f"{LABEL[regime]} — свіжий потік {fresh:.0f}\nчерез {T_MIN} ігр. хв: CO₂ у кімнатах з людьми до {worst:.2f} %, O₂ не нижче {o2min:.1f} %", fontsize=11)
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sm.set_array([])
fig.colorbar(sm, ax=axes.ravel().tolist(), fraction=0.02, pad=0.01, label="CO₂ зони, % (1,5 сонливість · 3 головний біль · 5 HP · 8 смерть)")
fig.suptitle(f"Повітря сектора seed={SEED}: CO₂ по зонах, 12 NPC у 3 спальнях і гравець у боксі за зачиненими дверима (AIR_SPEEDUP {AIR_SPEEDUP})", fontsize=13, y=0.995)
out = os.path.join(here, f"air_seed{SEED}.png")
plt.savefig(out, dpi=90, bbox_inches="tight")
print(out)
for regime in REGIMES:
    co2, o2, fresh, state, eta = simulate(regime)
    rooms_txt = ", ".join(f"{ppl} люд.: CO₂ {co2[z]:.2f} % O₂ {o2[z]:.1f} % [{state[z]}" + (f" {fmt_eta(eta[z])}" if state[z]=="countdown" else "") + "]"
                          for z, (cc, ppl) in zones.items() if ppl)
    print(f"  {regime:10s} свіжий {fresh:3.0f}: {rooms_txt}")

# --- контрольні числа специфікації (REQ-VENT-14/24, DEC-069), незалежно від карти ---
def hours_to(thr, c0, g, q, v, cin=C_OUT):
    ceq = cin + 100.0 * g / q if q > 0 else float("inf")
    return time_to(c0, ceq, q, v, g, thr)
print("Контрольні числа (ігрові години):")
print(f"  1 людина, герметизована клітинка 51 м³ → 3 %: {hours_to(3, C_OUT, G_PERSON, 0, V_CELL):.1f}, 8 %: {hours_to(8, C_OUT, G_PERSON, 0, V_CELL):.1f}")
print(f"  12 людей, герметизована станція 3 клітинки → 3 %: {hours_to(3, C_OUT, 12*G_PERSON, 0, 3*V_CELL):.1f}")
e = hours_to(1.5, C_OUT, 12*G_PERSON, Q_SLIT, 3*V_CELL)
print(f"  12 людей, станція 3 клітинки за зачиненими дверима (щілина {Q_SLIT:.0f}) → 1,5 %: {e*60:.0f} хв; C_рівн +{100*12*G_PERSON/Q_SLIT:.2f} %")
print(f"  12 людей, гілка 100 клітинок, шибер 0 → 3 %: {hours_to(3, C_OUT, 12*G_PERSON, 0, 100*V_CELL):.0f}")
# буржуйка в застійному тупику 3 клітинки з межею 1 (CO в од., 1 од. = 30 ppm; джерело 0,03 м³/год)
tau = 3*V_CELL / Q_STAG; ceq = 0.03 / Q_STAG * 1e6 / 30
print(f"  буржуйка в тупику 3 кл., межа 1: рівновага CO {ceq:.0f} од., 30 од. через {-tau*math.log(1-30/ceq)/AIR_SPEEDUP*60:.0f} хв, 60 через {-tau*math.log(1-60/ceq)/AIR_SPEEDUP*60:.0f} хв")
print(f"  застійних підзон на карті: {len(stag_zones)}, клітинок: {sum(len(cc) for cc, _ in stag_zones.values())}")
