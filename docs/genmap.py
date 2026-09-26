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
              ("Медпункт", 1), ("Торговий пост", 1), ("Пральня", 1), ("Генераторна", 1)]
rooms = []
cell = [[None] * N for _ in range(N)]
tries = 0
while sum(1 for _ in rooms) < 16 and tries < 3000:
    tries += 1
    h, w = rng.choice([(3, 3), (3, 5), (5, 3), (5, 5), (3, 7)])
    r0 = rng.randrange(1, N - h, 2); c0 = rng.randrange(1, N - w, 2)
    if abs(r0 - 1) + abs(c0 - 1) < 8: continue
    if any(abs(r0 - rr) < h + 3 and abs(c0 - cc) < w + 3 for rr, cc, _, _, _ in rooms): continue
    rtype = rng.choices([t for t, _ in ROOM_TYPES], [wt for _, wt in ROOM_TYPES])[0]
    rooms.append((r0, c0, h, w, rtype))
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            maze[r][c] = PATH; cell[r][c] = rtype

# 3. Петлі: прибрати ~6 % внутрішніх стін між проходами
walls = [(r, c) for r in range(1, N - 1) for c in range(1, N - 1) if maze[r][c] == WALL
         and ((maze[r - 1][c] == PATH and maze[r + 1][c] == PATH) or (maze[r][c - 1] == PATH and maze[r][c + 1] == PATH))]
for r, c in rng.sample(walls, int(len(walls) * 0.06)):
    maze[r][c] = PATH

# 4. Клімат: регіони Вороного
CLIMATES = [("Морозильна −18°C", "#9ecae1"), ("Холодна +4°C", "#deebf7"),
            ("Нейтральна +18°C", "#f7f7f7"), ("Тепла +27°C", "#fee0d2"), ("Гаряча +38°C", "#fc9272")]
seeds = [(rng.randrange(N), rng.randrange(N), i) for i in range(5)]
climate = [[min(seeds, key=lambda s: (s[0] - r) ** 2 + (s[1] - c) ** 2)[2] for c in range(N)] for r in range(N)]

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
ROOM_COLORS = {"Сейф-кімната": "#27ae60", "Спальня": "#8e44ad", "Кухня": "#f39c12", "Склад": "#7f8c8d",
               "Медпункт": "#e74c3c", "Торговий пост": "#f1c40f", "Пральня": "#3498db", "Генераторна": "#d35400"}
for r0, c0, h, w, t in rooms:
    ax.add_patch(Rectangle((c0, N - r0 - h), w, h, facecolor=ROOM_COLORS[t], alpha=0.55, edgecolor="black", lw=1.5))
    ax.text(c0 + w / 2, N - r0 - h / 2, t, ha="center", va="center", fontsize=6.5, weight="bold")
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
ax.set_title(f"Сектор 45×45, seed={SEED}  |  клітинка = 4×4 м (180×180 м)  |  шлях до шлюзу: {len(path)} кл. ≈ {len(path)*4} м", fontsize=12)
legend = [Patch(color="#2c3e50", label="Стіна (панель)")] + [Patch(color=col, label=n) for n, col in CLIMATES] + \
         [Patch(color=col, alpha=0.6, label=n) for n, col in ROOM_COLORS.items()] + \
         [plt.Line2D([], [], marker="o", color="#c0392b", ls="", mec="black", label="Заражений (спавн)"),
          plt.Line2D([], [], marker="s", color="#f1c40f", ls="", mec="black", label="Точка появи предмета"),
          plt.Line2D([], [], marker="^", color="#2980b9", ls="", mec="black", label="NPC"),
          plt.Line2D([], [], color="#2ecc71", label="Найкоротший шлях S→E")]
ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=4, fontsize=8, frameon=False)
plt.tight_layout()
out = f"sector_seed{SEED}.png"
plt.savefig(out, dpi=110)
print(out, "rooms:", len(rooms), "path:", len(path), "reachable:", len(dist))
