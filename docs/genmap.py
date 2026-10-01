import random, sys, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 71
N = 45
rng = random.Random(SEED)
WALL, PATH = 1, 0

# 1. Recursive backtracking (порт MazeGenerator з Maze-Rase)
maze = [[WALL] * N for _ in range(N)]
start = (1, 1)
maze[1][1] = PATH
stack = [start]
DIRS = [(0, 2), (2, 0), (0, -2), (-2, 0)]
while stack:
    r, c = stack[-1]
    nb = [(r + dr, c + dc) for dr, dc in DIRS
          if 0 < r + dr < N - 1 and 0 < c + dc < N - 1 and maze[r + dr][c + dc] == WALL]
    if nb:
        nr, nc = rng.choice(nb)
        maze[(r + nr) // 2][(c + nc) // 2] = PATH
        maze[nr][nc] = PATH
        stack.append((nr, nc))
    else:
        stack.pop()

# 2. Кімнати на непарних координатах
ROOM_TYPES = [("Сейф-кімната", 3), ("Спальня", 4), ("Кухня", 2), ("Склад", 3),
              ("Медпункт", 1), ("Торговий пост", 1), ("Пральня", 1), ("Генераторна", 1), ("Котельня", 1)]
# Гарантія MVP (13.1, рішення v1.2 за прототипом sim_survival.py): у кожному секторі є щонайменше по одній кімнаті
# кожного обов'язкового типу — без кухні (кран) гравець і NPC гинуть від спраги за 2 доби.
REQUIRED = ["Кухня", "Генераторна", "Котельня", "Сейф-кімната", "Спальня", "Склад", "Медпункт", "Торговий пост"]
rooms = []
cell = [[None] * N for _ in range(N)]
tries = 0
while sum(1 for _ in rooms) < 16 and tries < 3000:
    tries += 1
    h, w = rng.choice([(3, 3), (3, 5), (5, 3), (5, 5), (3, 7)])
    r0 = rng.randrange(1, N - h, 2); c0 = rng.randrange(1, N - w, 2)
    if abs(r0 - 1) + abs(c0 - 1) < 8: continue
    if any(abs(r0 - rr) < h + 3 and abs(c0 - cc) < w + 3 for rr, cc, _, _, _ in rooms): continue
    rtype = REQUIRED[len(rooms)] if len(rooms) < len(REQUIRED) else rng.choices([t for t, _ in ROOM_TYPES], [wt for _, wt in ROOM_TYPES])[0]
    rooms.append((r0, c0, h, w, rtype))
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            maze[r][c] = PATH; cell[r][c] = rtype

# 2a. Периметр і дверні прорізи (REQ-MAZE-02, DEC-077): кімната має стіни по периметру і 1–2 прорізи.
#     Кільце клітинок довкола кімнати замуровується; прорізом стає клітинка кільця, суміжна з коридором;
#     якщо без якогось кільцевого проходу частина лабіринту стає недосяжною, він відкривається як додатковий проріз.
def _bfs_all(src):
    d = {src}; q = collections.deque([src])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < N and 0 <= nc < N and maze[nr][nc] == PATH and (nr, nc) not in d:
                d.add((nr, nc)); q.append((nr, nc))
    return d
doors = {}   # (r0, c0) -> список клітинок-прорізів
for r0, c0, h, w, rtype in rooms:
    inside = {(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)}
    ring = [(r, c) for r in range(r0 - 1, r0 + h + 1) for c in range(c0 - 1, c0 + w + 1)
            if (r, c) not in inside and 0 < r < N - 1 and 0 < c < N - 1]
    open_ring = [p for p in ring if maze[p[0]][p[1]] == PATH]
    # кандидати в прорізи: клітинки кільця, що мають прохід назовні (не в кімнату і не в кільце)
    def leads_out(p):
        return any(0 <= p[0] + dr < N and 0 <= p[1] + dc < N and maze[p[0] + dr][p[1] + dc] == PATH
                   and (p[0] + dr, p[1] + dc) not in inside and (p[0] + dr, p[1] + dc) not in ring
                   for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    cands = [p for p in open_ring if leads_out(p)]
    for p in open_ring: maze[p[0]][p[1]] = WALL
    chosen = rng.sample(cands, min(len(cands), rng.choice([1, 2]))) if cands else []
    for p in chosen: maze[p[0]][p[1]] = PATH
    if not chosen and open_ring:                      # кімната без кандидатів — лишаємо один старий прохід
        p = rng.choice(open_ring); maze[p[0]][p[1]] = PATH; chosen = [p]
    # зв'язність: відкривати кільцеві проходи, поки всі проходи досяжні зі старту
    total = sum(row.count(PATH) for row in maze)
    #   спершу пробити стіну між відрізаною частиною і рештою лабіринту ПОЗА кільцем (нова петля коридору);
    #   лише якщо такої стіни немає — відкрити ще один проріз у кільці
    all_rings = {(r, c) for rr, cc, hh, ww, _ in rooms for r in range(rr - 1, rr + hh + 1) for c in range(cc - 1, cc + ww + 1)}
    while len(_bfs_all(start)) < total:
        reach = _bfs_all(start)
        def bridge(p):
            return any(0 < p[0] + dr < N - 1 and 0 < p[1] + dc < N - 1 and 0 < p[0] - dr < N - 1 and 0 < p[1] - dc < N - 1
                       and maze[p[0] + dr][p[1] + dc] == PATH and maze[p[0] - dr][p[1] - dc] == PATH
                       and ((p[0] + dr, p[1] + dc) in reach) != ((p[0] - dr, p[1] - dc) in reach)
                       for dr, dc in ((1, 0), (0, 1)))
        fix = next((p for p in ((r, c) for r in range(1, N - 1) for c in range(1, N - 1))
                    if maze[p[0]][p[1]] == WALL and p not in all_rings and bridge(p)), None)
        if fix is None:
            fix = next((p for p in open_ring if maze[p[0]][p[1]] == WALL and bridge(p)), None)
            if fix is None: break
            chosen.append(fix)
        maze[fix[0]][fix[1]] = PATH
    doors[(r0, c0)] = chosen

# 3. Петлі: прибрати ~6 % внутрішніх стін між проходами
_ring_cells = {(r, c) for r0, c0, h, w, _ in rooms for r in range(r0 - 1, r0 + h + 1) for c in range(c0 - 1, c0 + w + 1)
               if not (r0 <= r < r0 + h and c0 <= c < c0 + w)}
walls = [(r, c) for r in range(1, N - 1) for c in range(1, N - 1) if maze[r][c] == WALL and (r, c) not in _ring_cells
         and ((maze[r - 1][c] == PATH and maze[r + 1][c] == PATH) or (maze[r][c - 1] == PATH and maze[r][c + 1] == PATH))]
for r, c in rng.sample(walls, int(len(walls) * 0.06)):
    maze[r][c] = PATH

# 4. Клімат: регіони Вороного (12.1)
# ПРОЄКТНА ТЕМПЕРАТУРА регіону («за проєктом») — одна з п'яти проєктних зон, по одній на регіон, у фіксованому порядку (як у v1.0).
# Це свідома умовність заради КОНТРАСТУ між регіонами, а не фізика рівня: −18 поруч із +38
# у справному бункері неможливо, але так сектор читається і дає різний виклик у різних кутах.
PALETTE = [("Морозильна", -30.0), ("Холодна", 0.0), ("Нейтральна", 20.0), ("Тепла", 40.0), ("Гаряча", 58.0)]   # v1.2: подача гарячіша за назву, щоб КОРИДОР лягав у свою смугу (12.9.6)
setpoint = [t for _, t in PALETTE]
region_temp = setpoint  # сумісність зі старими посиланнями
BANDS = [(-99, -5, "Морозильна", "#9ecae1"), (-5, 12, "Холодна", "#deebf7"),
         (12, 24, "Нейтральна", "#f7f7f7"), (24, 30, "Тепла", "#fee0d2"),
         (30, 99, "Гаряча", "#fc9272")]   # v1.2: межа Гарячої +30 (було +32)
# Кімнати з власною температурою: від регіону не залежать (12.1).
ROOM_OWN_TEMP = {"Генераторна": (35, 40)}

def band(t):
    return next((n, col) for lo, hi, n, col in BANDS if lo <= t < hi)

# Стан кліматичної установки (12.6, 12.7.2) — другий аргумент: off | generator | pump | boiler
#   off       — нічого не працює: усе сповзає до породи +9
#   generator — генератор працює, насос котельні зламаний: рекуперація гріє ЛИШЕ гілку генераторної
#   pump      — генератор + полагоджений насос: +15 рекуперації розходиться по всіх калориферах
#   boiler    — генератор + насос + котел: контур тримає проєктну температуру (потрібен для Тепла і Гаряча)
# Термостат калорифера ніколи не подає вище проєктної: T_подачі = min(T_проєкт, тепло контуру).
STATE = sys.argv[2] if len(sys.argv) > 2 else "off"
assert STATE in ("off", "generator", "pump", "boiler"), STATE
T_ROCK, RECUP = 9.0, 15.0
seeds = [(rng.randrange(N), rng.randrange(N), i) for i in range(5)]
climate = [[min(seeds, key=lambda s: (s[0] - r) ** 2 + (s[1] - c) ** 2)[2] for c in range(N)] for r in range(N)]

# гілка генераторної — єдина, що гріється рекуперацією без насоса
_gen = next(((r0 + h // 2, c0 + w // 2) for r0, c0, h, w, t in rooms if t == "Генераторна"), None)
gen_region = climate[_gen[0]][_gen[1]] if _gen else None

def supply_temp(i):
    """T_подачі гілки регіону i за станом установки (12.7.2)."""
    if STATE == "off":
        return T_ROCK
    if STATE == "generator":
        return min(setpoint[i], RECUP) if i == gen_region else T_ROCK
    if STATE == "pump":
        return min(setpoint[i], RECUP)
    return setpoint[i]                                   # boiler

# у сталому режимі регіон сходиться до T_подачі (12.7.2) — це і бачить гравець
actual = [supply_temp(i) for i in range(5)]
gen_room_temp = 38.0 if STATE != "off" else T_ROCK        # генераторна +35…+40 поки працює
# заливка за ФАКТИЧНОЮ температурою неперервною шкалою, а не лише за смугою:
# у стані generator +9 і +11.4 — обидва «Холодна», і різниці між гілками не було б видно
import matplotlib.colors as mcolors
_cmap, _norm = plt.get_cmap("coolwarm"), mcolors.Normalize(vmin=-30, vmax=58)   # уся палітра від Морозильної до Гарячої
def temp_color(t, alpha=0.6):
    r, g, b, _ = _cmap(_norm(t))
    return (1 - alpha) + alpha * r, (1 - alpha) + alpha * g, (1 - alpha) + alpha * b
CLIMATES = [(f"Регіон {i + 1}: {band(actual[i])[0]} {actual[i]:+.1f}°C (за проєктом {setpoint[i]:+.1f})",
             temp_color(actual[i])) for i in range(5)]

# 5. Вихід у випадковому куті, крім стартового
exit_ = rng.choice([(1, N - 2), (N - 2, 1), (N - 2, N - 2)])
maze[exit_[0]][exit_[1]] = PATH

# 6. Перевірка зв'язності (BFS) і відстані від старту
def bfs(src):
    d = {src: 0}; q = collections.deque([src])
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < N and 0 <= nc < N and maze[nr][nc] == PATH and (nr, nc) not in d:
                d[(nr, nc)] = d[(r, c)] + 1; q.append((nr, nc))
    return d
dist = bfs(start)
assert exit_ in dist, "вихід недосяжний — повторити з новим під-seed"

# 7. Точки появи
free = [(r, c) for r in range(1, N - 1) for c in range(1, N - 1) if maze[r][c] == PATH and cell[r][c] is None]
zombies = rng.sample([p for p in free if dist.get(p, 0) >= 12], 10)
deadends = [(r, c) for r, c in free if sum(maze[r + dr][c + dc] == PATH for dr, dc in ((1,0),(-1,0),(0,1),(0,-1))) == 1]
items = rng.sample(deadends, min(12, len(deadends)))
npcs = [(r0 + h // 2, c0 + w // 2) for r0, c0, h, w, t in rooms if t in ("Торговий пост", "Спальня")][:3]

# ---- малюнок ----
fig, ax = plt.subplots(figsize=(13, 13))
for r in range(N):
    for c in range(N):
        if maze[r][c] == WALL:
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color="#2c3e50"))
        else:
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=CLIMATES[climate[r][c]][1]))
# межі регіонів Вороного — щоб їх було видно і тоді, коли всі регіони в одній смузі (стан off)
for r in range(N):
    for c in range(N):
        if c + 1 < N and climate[r][c] != climate[r][c + 1]:
            ax.plot([c + 1, c + 1], [N - 1 - r, N - r], color="#7f8c8d", lw=0.9, ls=(0, (2, 2)))
        if r + 1 < N and climate[r][c] != climate[r + 1][c]:
            ax.plot([c, c + 1], [N - 1 - r, N - 1 - r], color="#7f8c8d", lw=0.9, ls=(0, (2, 2)))
ROOM_COLORS = {"Сейф-кімната": "#27ae60", "Спальня": "#8e44ad", "Кухня": "#f39c12", "Склад": "#7f8c8d",
               "Медпункт": "#e74c3c", "Торговий пост": "#f1c40f", "Пральня": "#3498db", "Генераторна": "#d35400", "Котельня": "#a04000"}
for r0, c0, h, w, t in rooms:
    ax.add_patch(Rectangle((c0, N - r0 - h), w, h, facecolor=ROOM_COLORS[t], alpha=0.55, edgecolor="black", lw=1.5))
    label = f"{t}\n{gen_room_temp:+.0f}°C" if t in ROOM_OWN_TEMP else t
    ax.text(c0 + w / 2, N - r0 - h / 2, label, ha="center", va="center", fontsize=6.5, weight="bold")
ax.add_patch(Rectangle((start[1], N - 1 - start[0]), 1, 1, color="#2ecc71", ec="black", lw=2))
ax.text(start[1] + 0.5, N - 1 - start[0] + 0.5, "S", ha="center", va="center", fontsize=9, weight="bold")
ax.add_patch(Rectangle((exit_[1], N - 1 - exit_[0]), 1, 1, color="#e74c3c", ec="black", lw=2))
ax.text(exit_[1] + 0.5, N - 1 - exit_[0] + 0.5, "E", ha="center", va="center", fontsize=9, weight="bold", color="white")
for r, c in zombies: ax.plot(c + 0.5, N - 1 - r + 0.5, "o", color="#c0392b", ms=9, mec="black")
for r, c in items: ax.plot(c + 0.5, N - 1 - r + 0.5, "s", color="#f1c40f", ms=7, mec="black")
for r, c in npcs: ax.plot(c + 0.5, N - 1 - r + 0.5, "^", color="#2980b9", ms=11, mec="black")

# шлях старт→вихід
prev = {}; d = {start: 0}; q = collections.deque([start])
while q:
    r, c = q.popleft()
    if (r, c) == exit_: break
    for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
        n = (r + dr, c + dc)
        if maze[n[0]][n[1]] == PATH and n not in d:
            d[n] = d[(r, c)] + 1; prev[n] = (r, c); q.append(n)
p = exit_; path = []
while p != start: path.append(p); p = prev[p]
ax.plot([c + 0.5 for r, c in path], [N - 1 - r + 0.5 for r, c in path], "-", color="#2ecc71", lw=1.2, alpha=0.8)

ax.set_xlim(0, N); ax.set_ylim(0, N); ax.set_aspect("equal"); ax.axis("off")
STATE_LABEL = {"off": "усе вимкнене → порода +9 °C", "generator": "генератор без насоса → гріє лише свою гілку",
               "pump": "генератор + насос → +15 °C у всіх гілках", "boiler": "генератор + насос + котел → за проєктом"}
ax.set_title(f"Сектор 45×45, seed={SEED}  |  5 регіонів Вороного, за проєктом −30 / 0 / +20 / +40 / +58 °C\n"
             f"стан установки: {STATE} — {STATE_LABEL[STATE]}  |  шлях до шлюзу: {len(path)} кл. ≈ {len(path)*4} м",
             fontsize=11, linespacing=1.4)
legend = [Patch(color="#2c3e50", label="Стіна (панель)")] + [Patch(color=col, label=n) for n, col in CLIMATES] + \
         [Patch(color=col, alpha=0.6, label=n) for n, col in ROOM_COLORS.items()] + \
         [plt.Line2D([], [], marker="o", color="#c0392b", ls="", mec="black", label="Заражений (спавн)"),
          plt.Line2D([], [], marker="s", color="#f1c40f", ls="", mec="black", label="Точка появи предмета"),
          plt.Line2D([], [], marker="^", color="#2980b9", ls="", mec="black", label="NPC"),
          plt.Line2D([], [], color="#2ecc71", label="Найкоротший шлях S→E")]
ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=4, fontsize=8, frameon=False)
plt.tight_layout()
out = f"sector_seed{SEED}.png" if STATE == "off" else f"sector_seed{SEED}_{STATE}.png"
plt.savefig(out, dpi=110)
print(out, "rooms:", len(rooms), "path:", len(path), "reachable:", len(dist))
print(f"  стан {STATE}: " + ", ".join(
      f"R{i+1} {actual[i]:+.1f}°C/{setpoint[i]:+.1f} ({band(actual[i])[0]})"
      + (" ←ген" if i == gen_region else "") for i in range(5)))
print("  кімнати з власною температурою:", ", ".join(
      f"{t} {ROOM_OWN_TEMP[t][0]}…{ROOM_OWN_TEMP[t][1]}°C" for t in
      sorted({t for *_, t in rooms} & set(ROOM_OWN_TEMP)) ) or "  —")
