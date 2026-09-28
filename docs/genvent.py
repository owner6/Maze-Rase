"""Схема вентиляції сектора поверх карти з genmap.py (той самий seed → та сама карта).

Модель (розділ 12.7, варіант B — одна припливна мережа):
  • Магістраль — витяжний ствол: збирає спрацьоване повітря з камер; вона ж прохідний лаз.
  • Камера гілки — витяжна точка гілки + заслінка.
  • Гілка — одна на кліматичний регіон Вороного; дерево труб (MST) НАГНІТАЄ в решітки, в один бік.
  • Решітки — припливні, одна роль. Кожна точка спавну заражених = решітка.
  • Зворотний потік — повітря повертається від решіток ПРОХОДАМИ (двері + коридори) до камери.
    Другої, витяжної мережі труб не існує; двері — ділянка повітроводу.
  • Зона обслуговування — клітинки, які гілка покриває припливом (BFS від решіток).
  • Застійна зона — СТАТИЧНА: прохід далі STAGNANT_DIST клітинок КОРИДОРАМИ від найближчої
    решітки. Рахується ОДИН РАЗ на початковій конфігурації сектора і заморожується: рух панелей
    її не перераховує, тож гравець вивчає карту раз і назавжди.
    (Манхеттен по сітці тут не годиться: розстановка решіток жадібно насичує сектор до кроку
    GRILLE_SPACING, тому манхеттенська відстань структурно не перевищує GRILLE_SPACING − 1,
    і при порозі 9 застійних клітинок не було б жодної — перевірено для кількох seed.)

Герметизація (панель Архітектора перекрила зворотний шлях) — явище динамічне, на статичній
схемі не показується; тут видно лише напрямок, у який повітря повертатиметься, поки шлях вільний.

Запуск: python genvent.py 2031
"""
import sys, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

# --- 1. Відтворити карту з genmap.py (усе до блоку малювання) ---
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "genmap.py"), encoding="utf-8").read().split("# ---- малюнок ----")[0]
g = {"__name__": "genmap", "sys": sys}
exec(src, g)
N, maze, rooms, climate, seeds, rng = g["N"], g["maze"], g["rooms"], g["climate"], g["seeds"], g["rng"]
start, exit_, zombies, npcs, PATH, CLIMATES, SEED = g["start"], g["exit_"], g["zombies"], g["npcs"], g["PATH"], g["CLIMATES"], g["SEED"]

GRILLE_SPACING = 7      # мін. відстань між коридорними решітками (клітинок)
STAGNANT_DIST = 9       # далі цього від решітки — застій повітря
BRANCH_COLORS = ["#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#d62728"]
BRANCH_NAMES = "12345"

def neighbors(r, c):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < N and 0 <= nc < N and maze[nr][nc] == PATH:
            yield nr, nc

path_cells = [(r, c) for r in range(N) for c in range(N) if maze[r][c] == PATH]

# --- 2. Серце: генераторна (або центр сектора, якщо її нема) ---
gen = next(((r0 + h // 2, c0 + w // 2) for r0, c0, h, w, t in rooms if t == "Генераторна"), (N // 2, N // 2))

# --- 3. Камери гілок: найближчий прохід до сіда кожного регіону ---
chambers = []
for sr, sc, i in seeds:
    cand = [p for p in path_cells if climate[p[0]][p[1]] == i]
    chambers.append(min(cand, key=lambda p: (p[0] - sr) ** 2 + (p[1] - sc) ** 2))

# --- 4. Решітки: кімнати + спавни заражених + коридорні з кроком ---
grilles = {}  # (r,c) -> branch index
def add_grille(p, kind):
    grilles[p] = (climate[p[0]][p[1]], kind)
for r0, c0, h, w, t in rooms:
    add_grille((r0 + h // 2, c0 + w // 2), "room")
for z in zombies:
    add_grille(z, "spawn")
corridor = [p for p in path_cells if p not in grilles and p not in (start, exit_)]
rng.shuffle(corridor)
for p in corridor:
    if all(abs(p[0] - q[0]) + abs(p[1] - q[1]) >= GRILLE_SPACING for q in grilles):
        add_grille(p, "corridor")

# --- 5. Зони обслуговування припливом: BFS коридорами від решіток ---
serve, dist = {}, {}
q = collections.deque()
for p, (b, _) in grilles.items():
    serve[p], dist[p] = b, 0; q.append(p)
while q:
    p = q.popleft()
    for n in neighbors(*p):
        if n not in serve:
            serve[n], dist[n] = serve[p], dist[p] + 1; q.append(n)

# --- 5a. Застійні зони (12.7.1): порахувати ЗАРАЗ і заморозити ---
# Це знімок початкової конфігурації: рух панелей його не оновлює, тому набір застійних
# клітинок фіксований для цього seed. Саме на це й розраховує гравець-інженер.
STAGNANT_FROZEN = frozenset(p for p in path_cells if dist.get(p, 99) > STAGNANT_DIST)
stagnant = sorted(STAGNANT_FROZEN)

# --- 5b. Зворотний потік: куди повітря піде, повертаючись до найближчої камери ---
ret_next, seen_ret = {}, set(chambers)
q = collections.deque(chambers)
while q:
    p = q.popleft()
    for n in neighbors(*p):
        if n not in seen_ret:
            seen_ret.add(n); ret_next[n] = p; q.append(n)

# --- 6. Труби гілки: MST (Прим) по Манхеттену від камери до решіток ---
def mst_edges(root, pts):
    edges, inside, rest = [], [root], [p for p in pts if p != root]
    while rest:
        a, b = min(((a, b) for a in inside for b in rest), key=lambda e: abs(e[0][0] - e[1][0]) + abs(e[0][1] - e[1][1]))
        edges.append((a, b)); inside.append(b); rest.remove(b)
    return edges
branch_edges = [mst_edges(chambers[i], [p for p, (b, _) in grilles.items() if b == i]) for i in range(5)]

# --- 7. Малюнок ---
fig, ax = plt.subplots(figsize=(13, 14.2))
X = lambda c: c + 0.5
Y = lambda r: N - 1 - r + 0.5
for r in range(N):
    for c in range(N):
        if maze[r][c] != PATH:
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color="#2c3e50"))
        else:
            col = BRANCH_COLORS[serve[(r, c)]] if (r, c) in serve else "#ffffff"
            ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=col, alpha=0.22))
for r, c in stagnant:
    ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, facecolor="none", hatch="////", edgecolor="#555", lw=0))
# зворотний потік проходами до камери (двері + коридори); проріджено, щоб не забивало кадр
for (r, c), (pr, pc) in ret_next.items():
    if (r + c) % 3: continue
    dr, dc = pr - r, pc - c
    ax.arrow(X(c), Y(r), dc * 0.42, -dr * 0.42, width=0.035, head_width=0.26,
             head_length=0.2, length_includes_head=True, color="#16a085", alpha=0.55, zorder=2)
for r0, c0, h, w, t in rooms:
    ax.add_patch(Rectangle((c0, N - r0 - h), w, h, facecolor="none", edgecolor="black", lw=1.4))
    ax.text(c0 + w / 2, N - r0 - h / 2 - 0.9, t, ha="center", va="center", fontsize=6, color="#222")

def L(a, b, **kw):  # ортогональна труба: спочатку по рядку, потім по стовпцю
    ax.plot([X(a[1]), X(b[1]), X(b[1])], [Y(a[0]), Y(a[0]), Y(b[0])], solid_capstyle="round", **kw)

for ch in chambers:  # магістраль (прохідна)
    L(gen, ch, color="#7f8c8d", lw=7, alpha=0.9, zorder=3)
    L(gen, ch, color="white", lw=2.2, ls=(0, (1.5, 1.5)), zorder=4)
for i, edges in enumerate(branch_edges):
    for a, b in edges:
        L(a, b, color=BRANCH_COLORS[i], lw=2.2, alpha=0.95, zorder=5)
for p, (b, kind) in grilles.items():
    if kind == "spawn":
        ax.plot(X(p[1]), Y(p[0]), "s", ms=9, color=BRANCH_COLORS[b], mec="#c0392b", mew=2.2, zorder=7)
    elif kind == "room":
        ax.plot(X(p[1]), Y(p[0]), "s", ms=8, color=BRANCH_COLORS[b], mec="black", mew=1.2, zorder=7)
    else:
        ax.plot(X(p[1]), Y(p[0]), "s", ms=6, color=BRANCH_COLORS[b], mec="black", mew=0.8, zorder=7)
for i, ch in enumerate(chambers):
    ax.plot(X(ch[1]), Y(ch[0]), "D", ms=15, color=BRANCH_COLORS[i], mec="black", mew=1.5, zorder=8)
    ax.text(X(ch[1]), Y(ch[0]), BRANCH_NAMES[i], ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=9)
ax.plot(X(gen[1]), Y(gen[0]), "o", ms=20, color="#d35400", mec="black", mew=2, zorder=8)
ax.text(X(gen[1]), Y(gen[0]), "♥", ha="center", va="center", fontsize=11, color="white", zorder=9)
ax.add_patch(Rectangle((start[1], N - 1 - start[0]), 1, 1, color="#2ecc71", ec="black", lw=2, zorder=6))
ax.text(X(start[1]), Y(start[0]), "S", ha="center", va="center", fontsize=9, weight="bold", zorder=9)
ax.add_patch(Rectangle((exit_[1], N - 1 - exit_[0]), 1, 1, color="#e74c3c", ec="black", lw=2, zorder=6))
ax.text(X(exit_[1]), Y(exit_[0]), "E", ha="center", va="center", fontsize=9, weight="bold", color="white", zorder=9)
for r, c in npcs:
    ax.plot(X(c), Y(r), "^", color="#2980b9", ms=11, mec="black", zorder=7)

ax.set_xlim(0, N); ax.set_ylim(0, N); ax.set_aspect("equal"); ax.axis("off")
counts = [sum(1 for b, _ in grilles.values() if b == i) for i in range(5)]
ax.set_title(f"Вентиляція сектора 45×45, seed={SEED}\n"
             f"5 припливних гілок · {len(grilles)} решіток · {len(stagnant)} застійних клітинок "
             f"(> {STAGNANT_DIST} кл. коридорами від решітки, заморожено від seed)",
             fontsize=11, linespacing=1.4)
legend = [Patch(color="#2c3e50", label="Стіна (панель)")] + \
         [Patch(color=BRANCH_COLORS[i], alpha=0.5, label=f"Гілка {BRANCH_NAMES[i]} — {CLIMATES[i][0]} ({counts[i]} реш.)") for i in range(5)] + \
         [Patch(facecolor="none", hatch="////", edgecolor="#555", label="Застійна зона (статична, від seed)"),
          plt.Line2D([], [], color="#7f8c8d", lw=6, label="Магістраль — витяжний ствол (лаз) + стояк опалення"),
          plt.Line2D([], [], color="#333", lw=2, label="Труба гілки — приплив (непрохідна)"),
          plt.Line2D([], [], color="#16a085", lw=2, alpha=0.7, label="Зворотний потік проходами до камери"),
          plt.Line2D([], [], marker="D", color="#888", ms=11, ls="", mec="black", label="Камера гілки — витяг + заслінка + калорифер"),
          plt.Line2D([], [], marker="o", color="#d35400", ms=12, ls="", mec="black", label="Генераторна («серце»)"),
          plt.Line2D([], [], marker="s", color="#aaa", ms=7, ls="", mec="black", label="Решітка припливна (коридор / кімната)"),
          plt.Line2D([], [], marker="s", color="#aaa", ms=8, ls="", mec="#c0392b", mew=2, label="Решітка-спавн заражених"),
          plt.Line2D([], [], marker="^", color="#2980b9", ls="", mec="black", label="NPC")]
ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3, fontsize=8, frameon=False)
plt.tight_layout(); fig.subplots_adjust(bottom=0.09, top=0.955)
out = os.path.join(here, f"vent_seed{SEED}.png")
plt.savefig(out, dpi=110)
print(out, "grilles:", len(grilles), "per branch:", counts,
      "stagnant:", len(stagnant), f"({100*len(stagnant)/len(path_cells):.1f}% проходів)")
