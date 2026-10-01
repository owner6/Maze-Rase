"""Ізометрична схема всього комплексу «Об'єкт 71»: 6 рівнів на глибинах 40…140 м (roadmap REQ-MAZE-07, REQ-CLIMATE-06),
1–2 сектори на рівень, ліфтова шахта, сходи на ключ-картки, вентшахта з двома оголовками (REQ-VENT-26), шлюз «Нуль».

Кожен сектор — справжня карта genmap.py (seed = SEED × 100 + рівень × 10 + сектор); у прототипі сектор 45 × 45
(у специфікації 71 × 71 — масштаб той самий, клітинка 4 м). Проєкція ізометрична, рівні розсунуті по вертикалі
(вертикаль перебільшена, щоб плити не перекривались); реальна глибина підписана.

Запуск: python genbunker3d.py [seed=2031]
Результат: docs/bunker3d_seed<seed>.png
"""
import sys, os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch, Polygon
from matplotlib.lines import Line2D

here = os.path.dirname(os.path.abspath(__file__))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 2031
PUBLIC = "--public" in sys.argv          # версія для публікації: без seed і технічних підписів
LEVELS = [  # (рівень, назва, глибина м, секторів, клімат, колір)
    (1, "Адміністративний: шлюз «Нуль», мозок Архітектора", 40, 1, "+10…+35 °C", "#c0392b"),
    (2, "Медичний: лабораторія, штами",   60, 1, "+18…+24 °C", "#8e44ad"),
    (3, "Житловий: спальні, кухні, пральні", 80, 2, "+16…+22 °C", "#27ae60"),
    (4, "Складський: морозильні камери", 100, 2, "−18…+4 °C", "#2980b9"),
    (5, "Технічний: старт, паливо, насосна", 120, 1, "+5…+12 °C", "#d35400"),
    (6, "Затоплений назавжди" if PUBLIC else "Затоплений назавжди: лише стан W, не карта (DEC-076)", 140, 0, "+7 °C вода", "#7f8c8d"),
]
GAP = 10          # клітинок між секторами рівня
ZSTEP = 78        # умовних одиниць між рівнями (20 м реальних)
COS, SIN = math.cos(math.radians(30)), math.sin(math.radians(30))

def iso(x, y, z):  # x вправо, y вглиб, z вгору → екран
    return (x - y) * COS, (x + y) * SIN + z

def load_sector(seed):
    src = open(os.path.join(here, "genmap.py"), encoding="utf-8").read().split("# ---- малюнок ----")[0]
    g = {"__name__": "genmap", "sys": sys, "__file__": os.path.join(here, "genmap.py")}
    sys.argv = [sys.argv[0], str(seed)]
    exec(src, g)
    rooms = g["rooms"]
    gen = next(((r0 + h // 2, c0 + w // 2) for r0, c0, h, w, t in rooms if t == "Генераторна"), (g["N"] // 2, g["N"] // 2))
    return g["N"], g["maze"], g["PATH"], rooms, g["start"], g["exit_"], gen

sectors = {(lvl, s): load_sector(SEED * 100 + lvl * 10 + s) for lvl, _, _, nsec, _, _ in LEVELS for s in range(nsec)}
N = sectors[(1, 0)][0]
zof = {lvl: -(i) * ZSTEP for i, (lvl, *_) in enumerate(LEVELS)}   # рівень 1 зверху
Z0 = ZSTEP * 1.2                                                    # поверхня

fig, ax = plt.subplots(figsize=(24, 40))
ax.set_aspect("equal"); ax.axis("off")

def cell_poly(x, y, z):
    return [iso(x, y, z), iso(x + 1, y, z), iso(x + 1, y + 1, z), iso(x, y + 1, z)]

def slab(ox, n, maze, PATH, rooms, z, col):
    walls, paths, room = [], [], []
    roomcells = {(r, c) for r0, c0, h, w, t in rooms for r in range(r0, r0 + h) for c in range(c0, c0 + w)}
    for r in range(n):
        for c in range(n):
            p = cell_poly(ox + c, r, z)
            (room if (r, c) in roomcells else (paths if maze[r][c] == PATH else walls)).append(p)
    ax.add_collection(PolyCollection(paths, facecolors="#efeee6", edgecolors="none", zorder=2))
    ax.add_collection(PolyCollection(room, facecolors="#cfdcf2", edgecolors="none", zorder=2))
    ax.add_collection(PolyCollection(walls, facecolors="#2c3e50", edgecolors="none", zorder=2))
    # товщина плити (стеля 3,2 м) — дві бічні грані
    d = 1.6
    ax.add_patch(Polygon([iso(ox, n, z), iso(ox + n, n, z), iso(ox + n, n, z - d), iso(ox, n, z - d)], closed=True, fc="#1f2a36", ec="none", zorder=1.9))
    ax.add_patch(Polygon([iso(ox + n, 0, z), iso(ox + n, n, z), iso(ox + n, n, z - d), iso(ox + n, 0, z - d)], closed=True, fc="#34495e", ec="none", zorder=1.9))
    ax.add_patch(Polygon([iso(ox, 0, z), iso(ox + n, 0, z), iso(ox + n, n, z), iso(ox, n, z)], closed=True, fc="none", ec=col, lw=2.2, zorder=3))

# поверхня
sx0, sx1, sy0, sy1 = -8, 2 * N + GAP + 8, -8, N + 8
ax.add_patch(Polygon([iso(sx0, sy0, Z0), iso(sx1, sy0, Z0), iso(sx1, sy1, Z0), iso(sx0, sy1, Z0)], closed=True, fc="#a3b18a", ec="#3a5a40", lw=2, alpha=0.35, zorder=0.5))
ax.text(*iso(sx0, sy1, Z0 + 1), "ПОВЕРХНЯ, 0 м", fontsize=12, color="#3a5a40", weight="bold", ha="left")

# шахти: ліфт і сходи у стику секторів, вентшахта над серцем сектора A рівня 1
xl, yl = N + GAP / 2, N / 2 + 5
xs_, ys_ = N + GAP / 2, N / 2 - 5
n1, _, _, _, _, exit1, gen1 = sectors[(1, 0)]
vx, vy = gen1[1] + 0.5, gen1[0] + 0.5
zbot = zof[6]
ax.plot(*zip(iso(xl, yl, zbot), iso(xl, yl, Z0)), color="#f1c40f", lw=9, solid_capstyle="butt", zorder=4)
ax.plot(*zip(iso(xs_, ys_, zbot), iso(xs_, ys_, zof[1])), color="#e67e22", lw=4, ls=(0, (3, 2)), zorder=4)
ax.plot(*zip(iso(vx, vy, zbot), iso(vx, vy, Z0 + 4)), color="#7f8c8d", lw=6, zorder=4)
ax.plot(*zip(iso(vx, vy, Z0 + 4), iso(vx, vy, Z0 + 9)), color="#7f8c8d", lw=6, zorder=4)
ax.plot(*iso(vx, vy, Z0 + 4), marker="v", ms=16, color="#2980b9", mec="k", zorder=5)
ax.plot(*iso(vx, vy, Z0 + 9), marker="^", ms=16, color="#e74c3c", mec="k", zorder=5)
tx, ty = iso(vx, vy, Z0 + 4); ax.text(tx - 3, ty - 3, "ЗАБІР повітря (нижній оголовок)", ha="right", fontsize=11, color="#2980b9", weight="bold", va="center")
tx, ty = iso(vx, vy, Z0 + 9); ax.text(tx + 3, ty, "ВИКИД (+6 м над забором)", fontsize=11, color="#c0392b", weight="bold", va="center")
tx, ty = iso(xl, yl, Z0); ax.text(tx + 3, ty + 6, "ЛІФТ (лише при живленні)", fontsize=11, color="#b7950b", weight="bold", va="center")
tx, ty = iso(xs_, ys_, zof[1]); ax.text(tx + 3, ty + 2, "СХОДИ (ключ-картки)", fontsize=11, color="#ca6f1e", weight="bold", va="center")

for i, (lvl, name, depth, nsec, clim, col) in enumerate(LEVELS):
    z = zof[lvl]
    for s in range(nsec):
        n, maze, PATH, rooms, start, exit_, gen = sectors[(lvl, s)]
        ox = s * (n + GAP)
        slab(ox, n, maze, PATH, rooms, z, col)
        ax.plot(*iso(ox + gen[1] + 0.5, gen[0] + 0.5, z), marker="o", ms=11, color="#d35400", mec="k", zorder=5)
        tx, ty = iso(ox, 0, z); ax.text(tx - 1, ty - 1, "AB"[s], fontsize=12, color=col, weight="bold", ha="right", va="top")
        if lvl == 5 and s == 0:
            ax.plot(*iso(ox + start[1] + 0.5, start[0] + 0.5, z), marker="s", ms=13, color="#2ecc71", mec="k", zorder=6)
            tx, ty = iso(ox + start[1] + 0.5, start[0] + 0.5, z); ax.text(tx - 2, ty, "СТАРТ", fontsize=11, weight="bold", color="#1e8449", ha="right", va="center")
        if lvl == 1 and s == 0:
            ex, ey = exit_[1] + 0.5, exit_[0] + 0.5
            ax.plot(*iso(ex, ey, z), marker="s", ms=13, color="#e74c3c", mec="k", zorder=6)
            ax.plot(*zip(iso(ex, ey, z), iso(ex, ey - 10, Z0)), color="#e74c3c", lw=4, zorder=4)
            tx, ty = iso(ex, ey - 10, Z0); ax.text(tx - 3, ty + 4, "ШЛЮЗ «НУЛЬ» → поверхня", ha="right", fontsize=11, weight="bold", color="#c0392b", va="center")
    if nsec == 0:   # затоплений рівень: суцільна водна плита
        ax.add_patch(Polygon([iso(0, 0, z), iso(2 * N + GAP, 0, z), iso(2 * N + GAP, N, z), iso(0, N, z)], closed=True, fc="#5dade2", ec=col, lw=2.2, alpha=0.75, zorder=2))
        tx, ty = iso(N + GAP / 2, N / 2, z); ax.text(tx, ty, "ВОДА", fontsize=16, weight="bold", color="#1b4f72", ha="center", va="center", zorder=6)
    if nsec == 2:
        ax.plot(*zip(iso(N, N / 2, z), iso(N + GAP, N / 2, z)), color="#555", lw=7, zorder=3.5)
    # з'єднання секторів із шахтами
    ax.plot(*zip(iso(N, N / 2 + 3, z), iso(xl, yl, z)), color="#f1c40f", lw=3, zorder=3.5)
    ax.plot(*zip(iso(N, N / 2 - 3, z), iso(xs_, ys_, z)), color="#e67e22", lw=2, ls=(0, (3, 2)), zorder=3.5)
    tx, ty = iso(-2, N, z)
    ax.text(tx - 4, ty, f"Рівень {lvl} · −{depth} м · порода {9 + 0.03 * (depth - 40):+.1f} °C · {clim}\n{name}",
            fontsize=12, color=col, weight="bold", ha="right", va="center")

ax.autoscale_view()
if PUBLIC:
    ax.set_title("«Об'єкт 71»: шість рівнів під Карпатами, від 40 до 140 м\nп'ять прохідних, шостий затоплений; шлях до виходу: старт (5) → 4 → 3 → 2 → 1 → шлюз «Нуль»", fontsize=16, weight="bold")
else:
    ax.set_title(f"«Об'єкт 71», seed {SEED}: 6 рівнів (5 прохідних, шостий затоплений), {sum(l[3] for l in LEVELS)} секторів, глибина 40…140 м (16 м скелі між рівнями, стеля 3,2 м, клітинка 4 м)\n"
             "ізометрія з перебільшеною вертикаллю; кожен сектор — реальна карта genmap.py свого seed; шлях гравця: старт (5) → 4 → 3 → 2 → 1 → шлюз «Нуль»",
             fontsize=14)
legend = [Patch(color="#2c3e50", label="Стіна (панель на рейці)"), Patch(color="#cfdcf2", label="Кімната"), Patch(color="#efeee6", label="Коридор"),
          Line2D([], [], marker="o", color="#d35400", ls="", mec="k", ms=10, label="Генераторна (серце сектора, вентшахта)"),
          Line2D([], [], color="#f1c40f", lw=6, label="Ліфтова шахта"), Line2D([], [], color="#e67e22", lw=3, ls=(0, (3, 2)), label="Сходи між рівнями"),
          Line2D([], [], color="#7f8c8d", lw=5, label="Вентшахта: магістральний стояк + оголовки"),
          Line2D([], [], color="#555", lw=6, label="Тунель між секторами рівня"),
          Line2D([], [], marker="s", color="#2ecc71", ls="", mec="k", ms=10, label="Старт"), Line2D([], [], marker="s", color="#e74c3c", ls="", mec="k", ms=10, label="Шлюз «Нуль»")]
ax.legend(handles=legend, loc="upper right", fontsize=11, framealpha=0.95)
out = os.path.join(here, "bunker3d_public.png" if PUBLIC else f"bunker3d_seed{SEED}.png")
plt.savefig(out, dpi=70, bbox_inches="tight")
print(out)
