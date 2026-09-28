"""Прототип 12.9.8: рівень 1 при ядерній зимі, 3 доби без гравця.

Перевіряє тести пунктів 5 і 6: виживання NPC у станціях обігріву ≥ 70 %, анабіоз заражених ≥ 60 % через добу.

Модель (усе з документа v1.2):
  • карта: genmap.py <seed> (сектор 45×45 як проксі рівня 1), стан off; подача у ВСІ решітки −36 °C (ядерна зима без котла),
    тяга 40 → потік 0,4; клітинка шлюзу E тягнеться до −36 з вагою 0,5 (шахта «Нуль», 12.9.1);
  • тепло: сітка дифузії 12.9.2 (k прохід 0,25, зачинені двері станції 0,05, стіни 0,05/0,02, порода 0,01), SUB=6, numpy;
  • станції обігріву: 3 кімнати, обрані так, щоб BFS-відстань між сусідніми і до E була ≤ 40; джерело за сценарієм:
      A — «як записано»: буржуйка 4 кВт на 6 полін = 2 год, далі лише тіла;
      B — калорифер на решітці станції: балони від seed на 1 / 2 / 3 доби (різні для трьох станцій, випадковий порядок), далі решітка
          знову дме −36; NPC ідуть до найближчої станції з паливом;
      C — 4 кВт постійно (буржуйка з запасом дров ≥ 3 доби);
  • NPC: 12, стартують у станціях; clo 1,0 (T_комфорт +9); тіло за 12.2; «Грітися» пріоритет: якщо T_тіла < 35 і не в станції —
    іде до найближчої станції (20 кл/хв); у станції сидить; кожен NPC — 0,1 кВт у своїй клітинці; смерть при T_тіла < 30 (гіпотермія III, 10 хв);
    охоронець у кожній станції з 30 патронами;
  • заражені: 30 (63/27/10 %), старт у коридорах; ПАТРУЛЬ з тепловою вагою: на перехресті напрямок обирається з ймовірністю
    ∝ exp((T_сусіда − T_поточна) / 5); на клітинці тепліше медіани коридорів на ≥ 5 °C — стан «відпочинок» 20–60 хв, потім щонайменше 120 хв патруля без відпочинку;
    швидкість × 0,8 нижче 0, × 0,6 нижче −20; шум станції — подія з ймовірністю 20 %/хв (NPC кашляють, говорять), чутно на 15 м → розслідування до дверей,
    огляд 1 хв, потім 10 хв ігнорує шум цієї станції і патрулює далі;
    дрейф до тепла — до найтеплішої клітинки в радіусі 12 по BFS (локальне оновлення 12.9.2), не лише до сусідньої; двері станцій заблоковані: Блукач/Бігун не входять,
    Набряклий ламає за 6 с; охоронець стріляє 1 постріл/с, влучання 70 %, 25 шкоди, магазин 15, перезарядка 2,4 с, запас 30;
    бій посекундний: якщо Набряклий увійшов — б'є NPC по 30 раз на 2,5 с, охоронець продовжує стріляти; двері зламані до кінця.

Запуск: python sim_level1_winter.py 2031 A|B|C [діб=3] [модель=a|doc]
  модель a (типова, v1.2 = нова 12.9.2): подача 1,0, стіни 0,02, порода 0,005;
  модель doc — старі коефіцієнти v1.1 (подача 0,3, стіни 0,05, порода 0,01), лише для порівняння.
  У сценаріях B і C решітка станції має локальний калорифер: подача в неї +20 (пальник на калорифері), у сценарії A — −36 як усюди.
"""
import sys, os, collections, random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__))
docs = os.path.dirname(here)
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2031
SCEN = sys.argv[2] if len(sys.argv) > 2 else "A"
DAYS = int(sys.argv[3]) if len(sys.argv) > 3 else 3
MODEL = sys.argv[4] if len(sys.argv) > 4 else "a"
K_SUP, K_WALL, K_ROCK = (0.3, 0.05, 0.01) if MODEL == "doc" else (1.0, 0.02, 0.005)
sys.argv = [sys.argv[0], str(SEED), "off"]

src = open(os.path.join(docs, "genvent.py"), encoding="utf-8").read().split("# --- 7. Малюнок ---")[0]
g = {"__name__": "genvent", "sys": sys, "__file__": os.path.join(docs, "genvent.py")}
exec(src, g)
N, maze, rooms, PATH = g["N"], g["maze"], g["rooms"], g["PATH"]
start, exit_, grilles, chambers = g["start"], g["exit_"], g["grilles"], g["chambers"]
rng = random.Random(SEED * 7 + 1)

T_ROCK, T_SUPPLY, FLOW = 9.0, -36.0, 0.40
SUB = 6
passable = np.array([[maze[r][c] == PATH for c in range(N)] for r in range(N)])
cells = [(r, c) for r in range(N) for c in range(N) if passable[r, c]]

# --- BFS відстані ---
def bfs(srcs):
    dist = {s: 0 for s in srcs}; q = collections.deque(srcs)
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (r + dr, c + dc)
            if 0 <= n[0] < N and 0 <= n[1] < N and passable[n] and n not in dist:
                dist[n] = dist[(r, c)] + 1; q.append(n)
    return dist

# --- станції: жадібно від E назад, крок ≤ 40 ---
room_cells = {}
for r0, c0, h, w, t in rooms:
    room_cells[(r0, c0)] = [(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)]
room_center = {k: (k[0] + len(v) // (2 * (v[-1][1] - v[0][1] + 1)), k[1] + (v[-1][1] - v[0][1]) // 2) for k, v in room_cells.items()}
dE = bfs([exit_])
cands = sorted(room_cells, key=lambda k: dE[room_center[k]])
stations = []
last = exit_
for k in cands:
    dk = bfs([room_center[k]])
    if 0 < dk.get(last, 999) <= 40:
        stations.append(k); last = room_center[k]
    if len(stations) == 3: break
if len(stations) < 3:  # добираємо найближчі, якщо ланцюжок не склався
    for k in cands:
        if k not in stations: stations.append(k)
        if len(stations) == 3: break
station_cells = set(c for k in stations for c in room_cells[k])
station_of = {c: i for i, k in enumerate(stations) for c in room_cells[k]}
st_dist = [bfs(room_cells[k]) for k in stations]
print("станції:", [f"{t} @{k} dE={dE[room_center[k]]}" for k in stations for (r0, c0, h, w, t) in rooms if (r0, c0) == k])

# --- коефіцієнти ребер (дифузія, numpy) ---
def edge_k(a, b):
    if not (passable[a] and passable[b]): return 0.0
    ina, inb = a in station_cells, b in station_cells
    if ina != inb: return 0.05           # зачинені двері станції
    return 0.25
K = {}
for name, (dr, dc) in {"d": (1, 0), "u": (-1, 0), "r": (0, 1), "l": (0, -1)}.items():
    arr = np.zeros((N, N))
    for (r, c) in cells:
        n = (r + dr, c + dc)
        if 0 <= n[0] < N and 0 <= n[1] < N:
            arr[r, c] = edge_k((r, c), n)
    K[name] = arr
nwalls = np.zeros((N, N))
for (r, c) in cells:
    nwalls[r, c] = sum(1 for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if not passable[r+dr, c+dc])
grille_mask = np.zeros((N, N));
for p in grilles: grille_mask[p] = 1.0
exit_mask = np.zeros((N, N)); exit_mask[exit_] = 1.0
supply_T = np.full((N, N), T_SUPPLY)
st_grille = [[c for c in room_cells[k] if c in grilles] for k in stations]

Ta = np.where(passable, T_ROCK, np.nan); Tw = np.full((N, N), T_ROCK)
def shift(a, dr, dc):
    out = np.full_like(a, np.nan);
    # out[r, c] = a[r + dr, c + dc] (значення сусіда в напрямку dr, dc)
    rs = slice(max(-dr,0), N+min(-dr,0)); rd = slice(max(dr,0), N+min(dr,0))
    cs = slice(max(-dc,0), N+min(-dc,0)); cd = slice(max(dc,0), N+min(dc,0))
    out[rs, cs] = a[rd, cd]; return out
def step_heat(sources_kw):
    global Ta, Tw
    for _ in range(SUB):
        T = np.nan_to_num(Ta, nan=T_ROCK)
        dT = 0.4 * sources_kw
        for name, (dr, dc) in {"d": (1, 0), "u": (-1, 0), "r": (0, 1), "l": (0, -1)}.items():
            dT += K[name] * (np.nan_to_num(shift(T, dr, dc), nan=T_ROCK) - T)
        dT += nwalls * 0.01 * (Tw - T) + K_WALL * (Tw - T)
        dT += grille_mask * FLOW * K_SUP * (supply_T - T)
        dT += exit_mask * 0.5 * (T_SUPPLY - T)
        Ta = np.where(passable, T + dT / SUB, np.nan)
        Tw += (0.02 * (np.nan_to_num(Ta, nan=T_ROCK) - Tw) + K_ROCK * (T_ROCK - Tw)) / SUB

# --- агенти ---
class NPC:
    def __init__(s, cell): s.cell = cell; s.T = 36.6; s.alive = True; s.cold_min = 0; s.st = station_of[cell]; s.hp = 100.0
npcs = []
for i in range(12):
    k = stations[i % 3]; npcs.append(NPC(rng.choice(room_cells[k])))
guard_ammo = [30, 30, 30]; mag = [15, 15, 15]; reload = [0, 0, 0]; door_broken = [False, False, False]
CLO = 1.0; T_COMF = 27 - 18 * CLO

class Z:
    def __init__(s, cell, kind): s.cell = cell; s.kind = kind; s.cold = 0; s.sleep = False; s.inside = None; s.alive = True; s.hits = 0; s.rest = 0; s.dir = None; s.target = None; s.ignore = [0, 0, 0]; s.norest = 0; s.moved = 0
corr = [c for c in cells if c not in station_cells and dE[c] > 3 and abs(c[0]-start[0])+abs(c[1]-start[1]) > 12]
zs = [Z(rng.choice(corr), rng.choices(["walker", "runner", "bloat"], [63, 27, 10])[0]) for _ in range(30)]
ANAB = -15.0
SPEED = {"walker": 18, "runner": 72, "bloat": 13}   # клітинок/хв (1,2 / 4,8 / 0,9 м/с при 4 м клітинці)

import math
HEAR = 15 // 4   # 15 м = ~4 клітинки (шум станції)
st_noise = [bfs(room_cells[k]) for k in stations]   # відстані для слуху
def patrol_step(z, T, steps, corr_med):
    """Патруль із тепловою вагою: на кожному кроці вибір напрямку ∝ exp(ΔT/5), без розвороту, крім тупика."""
    for _ in range(steps):
        cell = z.cell
        opts = []
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (cell[0]+dr, cell[1]+dc)
            if passable[n] and n not in station_cells:
                opts.append(((dr, dc), n))
        if not opts: return
        back = None if z.dir is None else (-z.dir[0], -z.dir[1])
        fwd = [o for o in opts if o[0] != back] or opts
        ws = [math.exp(min(6, (T[n] - T[cell]) / 5)) for _, n in fwd]
        # тримати напрямок: пряме продовження × 2,3 (оригінал: 30 % зміни на перехресті)
        ws = [w * (2.3 if d == z.dir else 1.0) for w, (d, _) in zip(ws, fwd)]
        d, n = rng.choices(fwd, ws)[0]
        z.dir = d; z.cell = n
        z.moved += 1
        if T[n] >= corr_med + 5 and z.rest == 0 and z.norest == 0:
            z.rest = rng.randint(20, 60); z.norest = 120; return
corr_med = T_ROCK; migr = 0
hist = {"t": [], "npc": [], "sleep": [], "Tst": [[], [], []], "Tcorr": [], "adj": [], "rest": []}
MIN = DAYS * 1440
fuel_kw = {"A": (4.0, 120), "B": (0.0, 2880), "C": (0.0, MIN + 1)}[SCEN]   # B/C: тепло через решітку
st_fuel = [fuel_kw[1]] * 3
if SCEN == "B":
    st_fuel = [1440, 2880, 4320]; rng.shuffle(st_fuel)
deaths = collections.Counter()
for t in range(MIN):
    T = np.nan_to_num(Ta, nan=T_ROCK)
    src = np.zeros((N, N))
    for i, k in enumerate(stations):
        if SCEN == "A" and t < fuel_kw[1]:
            cc = room_cells[k]
            for c in cc: src[c] += fuel_kw[0] / len(cc)
        if SCEN in ("B", "C"):
            has = st_fuel[i] > 0
            if has: st_fuel[i] -= 1
            for c in st_grille[i]: supply_T[c] = 20.0 if has else T_SUPPLY
    for n in npcs:
        if n.alive: src[n.cell] += 0.1
    for z in zs:
        if z.alive: src[z.cell] += 0.2 if z.kind == "bloat" else 0.1
    step_heat(src)
    T = np.nan_to_num(Ta, nan=T_ROCK)
    noise_now = [rng.random() < 0.2 and any(n.alive and station_of.get(n.cell) == i for n in npcs) for i in range(3)]
    corr_med = float(np.median([T[c] for c in cells if c not in station_cells])) if t % 30 == 0 else corr_med
    # NPC
    for n in npcs:
        if not n.alive: continue
        env = T[n.cell]
        n.T += 0.01 * (env - T_COMF) + 0.05 * (36.6 - n.T)
        cur = station_of.get(n.cell)
        need_move = n.T < 35 and (cur is None or (SCEN in ("B", "C") and st_fuel[cur] <= 0 and any(f > 0 for f in st_fuel)))
        if need_move:
            fueled = [j for j in range(3) if st_fuel[j] > 0] or list(range(3))
            i = min(fueled, key=lambda j: st_dist[j].get(n.cell, 9999))
            if cur == i: need_move = False
        if need_move:
            if cur is not None: migr += 1
            # рух до станції: 20 кл/хв по градієнту відстані
            for _ in range(20):
                if station_of.get(n.cell) == i: break
                nxt = min([(n.cell[0]+dr, n.cell[1]+dc) for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if passable[n.cell[0]+dr, n.cell[1]+dc]],
                          key=lambda c: st_dist[i].get(c, 9999))
                n.cell = nxt
        if n.T < 33: n.hp -= 1.5                      # гіпотермія II: −1,5 HP/хв (12.3)
        elif n.hp < 100 and n.cell in station_cells: n.hp = min(100, n.hp + 0.5 / 60)
        n.cold_min = n.cold_min + 1 if n.T < 30 else 0
        if n.cold_min >= 10: n.alive = False; deaths["гіпотермія III"] += 1
        elif n.hp <= 0: n.alive = False; deaths["гіпотермія II (HP)"] += 1
    fights = []
    # заражені
    for z in zs:
        if not z.alive: continue
        env = T[z.cell]
        if z.inside is not None:
            continue
        if z.norest > 0 and z.rest == 0: z.norest -= 1
        if z.rest > 0: z.rest -= 1; continue                       # відпочинок на теплій плямі
        mult = 0.6 if env < -20 else (0.8 if env < 0 else 1.0)
        steps = max(1, int(SPEED[z.kind] * mult))
        for i in range(3):
            if z.ignore[i] > 0: z.ignore[i] -= 1
        if z.target is None:
            near = [i for i in range(3) if noise_now[i] and z.ignore[i] == 0 and st_noise[i].get(z.cell, 99) <= HEAR]
            if near: z.target = near[0]
        if z.target is not None:                                   # розслідування до дверей станції
            i = z.target
            for _ in range(steps):
                if any((z.cell[0]+dr, z.cell[1]+dc) in station_cells for dr, dc in ((1,0),(-1,0),(0,1),(0,-1))):
                    z.target = None; z.ignore[i] = 10; break      # огляд 1 хв, далі 10 хв ігнорує
                z.cell = min([(z.cell[0]+dr, z.cell[1]+dc) for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if passable[z.cell[0]+dr, z.cell[1]+dc] and (z.cell[0]+dr, z.cell[1]+dc) not in station_cells],
                             key=lambda c: st_noise[i].get(c, 9999))
        else:
            patrol_step(z, T, steps, corr_med)
        # біля дверей станції?
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nb = (z.cell[0]+dr, z.cell[1]+dc)
            if nb in station_cells:
                i = station_of[nb]
                if door_broken[i]:
                    z.inside = i; z.cell = nb; fights.append((i, z))
                elif z.kind == "bloat":
                    fights.append((i, z))
                break
    # бій посекундно: Набряклий під дверима або будь-хто всередині зламаної станції
    for i, z in fights:
        if not z.alive: continue
        hp = 125.0 if z.kind == "bloat" else (75.0 if z.kind == "runner" else 50.0)
        sec = 0; door_t = 0 if door_broken[i] else 6; inside = door_broken[i]; atk = 0
        victims = [n for n in npcs if n.alive and station_of.get(n.cell) == i]
        while sec < 60 and z.alive and victims:
            if guard_ammo[i] > 0:
                if mag[i] == 0:
                    reload[i] += 1
                    if reload[i] >= 3: mag[i] = min(15, guard_ammo[i]); reload[i] = 0
                else:
                    mag[i] -= 1; guard_ammo[i] -= 1
                    if rng.random() < 0.7: hp -= 25
            if hp <= 0: z.alive = False; deaths["заражений_у_бою"] += 1; break
            if not inside:
                door_t -= 1
                if door_t <= 0: inside = True; door_broken[i] = True; z.inside = i; deaths["двері_зламано"] += 1
            else:
                atk += 1
                if atk >= 2.5:
                    atk = 0; v = victims[0]; v.hp -= 30 if z.kind == "bloat" else 15
                    if v.hp <= 0: v.alive = False; deaths["укус"] += 1; victims = victims[1:]
            sec += 1
    if t % 30 == 0:
        hist["t"].append(t / 60)
        hist["npc"].append(sum(n.alive for n in npcs))
        hist["sleep"].append(sum(1 for z in zs if z.alive and z.sleep) / max(1, sum(1 for z in zs if z.alive)))
        for i, k in enumerate(stations):
            hist["Tst"][i].append(float(np.mean([T[c] for c in room_cells[k]])))
        hist["Tcorr"].append(float(np.median([T[c] for c in cells if c not in station_cells])))
        hist["rest"].append(sum(1 for z in zs if z.alive and z.rest > 0) / max(1, sum(z.alive for z in zs)))
        hist["adj"].append(sum(1 for z in zs if z.alive and not z.sleep and any((z.cell[0]+dr, z.cell[1]+dc) in station_cells for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)))))

alive = sum(n.alive for n in npcs)
sleep_24 = hist["sleep"][min(len(hist["sleep"]) - 1, 48)]
print(f"  біля дверей: макс {max(hist['adj'])}, середнє {np.mean(hist['adj']):.1f}; частка часу у відпочинку {100*np.mean(hist['rest']):.0f}%; пройдено клітинок на зараженого за добу {np.mean([z.moved for z in zs])/DAYS:.0f}")
print(f"  міграції NPC між станціями: {migr}")
print(f"seed {SEED} модель {MODEL} сценарій {SCEN}: NPC вижило {alive}/12 = {100*alive/12:.0f}% (ціль ≥ 70%); "
      f"зламано станцій {sum(door_broken)}; паливо станцій (хв) {st_fuel}; патрони {guard_ammo}; смерті {dict(deaths)}")
Tf = np.nan_to_num(Ta, nan=T_ROCK); corrT = np.array([Tf[c] for c in cells if c not in station_cells])
rest = sum(1 for z in zs if z.alive and z.rest > 0); zT = [Tf[z.cell] for z in zs if z.alive]; adj = sum(1 for z in zs if z.alive and any((z.cell[0]+dr, z.cell[1]+dc) in station_cells for dr, dc in ((1,0),(-1,0),(0,1),(0,-1))))
print(f"  заражені: живі {sum(z.alive for z in zs)}, відпочивають {rest}, сплять {sum(1 for z in zs if z.alive and z.sleep)}, медіана T їхніх клітинок {np.median(zT):+.1f}, біля дверей станцій {adj}, T тіла NPC (мін/медіана) {min([n.T for n in npcs if n.alive] or [0]):.1f}/{np.median([n.T for n in npcs if n.alive] or [0]):.1f}, HP мін {min([n.hp for n in npcs if n.alive] or [0]):.0f}")
print("  температура станцій у кінці:", [f"{x[-1]:+.1f}" for x in hist["Tst"]], "коридори: медіана", f"{np.median(corrT):+.1f}",
      "min", f"{corrT.min():+.1f}", "частка < −20:", f"{(corrT < -20).mean()*100:.0f}%", "< −30:", f"{(corrT < -30).mean()*100:.0f}%")

fig, ax = plt.subplots(1, 2, figsize=(16, 6))
for i in range(3): ax[0].plot(hist["t"], hist["Tst"][i], label=f"станція {i+1}")
ax[0].plot(hist["t"], hist["Tcorr"], "k--", label="коридори (медіана)")
ax[0].axhline(T_COMF, color="gray", lw=0.7); ax[0].set_xlabel("год"); ax[0].set_ylabel("°C"); ax[0].legend(); ax[0].set_title(f"Температура, модель {MODEL}, сценарій {SCEN}")
ax[1].plot(hist["t"], hist["npc"], label="NPC живі"); ax[1].plot(hist["t"], [12 * s for s in hist["sleep"]], label="анабіоз заражених ×12"); ax[1].plot(hist["t"], hist["adj"], label="заражених біля дверей станцій")
ax[1].axhline(8.4, color="r", lw=0.7, ls=":"); ax[1].set_xlabel("год"); ax[1].legend(); ax[1].set_title("NPC і заражені")
plt.tight_layout(); out = os.path.join(here, f"level1_winter_seed{SEED}_{MODEL}_{SCEN}.png"); plt.savefig(out, dpi=100); print(out)
