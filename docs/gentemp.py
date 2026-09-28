"""Динаміка температури по клітинках і потоки повітря поверх карти genmap.py + genvent.py.

Ліва панель — ТЕМПЕРАТУРА ПОВІТРЯ після T_MIN ігрових хвилин за сіткою дифузії (12.9.2, коефіцієнти v1.2):
  крок 1 джерела: T += 0,4 × P_кВт (генераторна +6 кВт, буржуйка +4 кВт у першій спальні, компресора немає);
  крок 2 сусіди:   T += k × (T_сусід − T), k = 0,25 прохід, 0,01 бетонна стіна (крізь панель 0,03);
  крок 3 стіни:    T_ст += 0,02 × (T − T_ст); T += 0,02 × (T_ст − T);   (v1.2, варіант (а) 12.9.6)
  крок 4 порода:   T_ст += 0,005 × (9 − T_ст);
  крок 5 подача:   під решіткою T += потік × 1,0 × (T_подачі − T); на зворотному шляху T += потік × 0,1 × (T_попер − T).
T_подачі гілки береться з genmap.py за станом установки (off | generator | pump | boiler).
Це модель EPIC-29; для MVP (теплові об'єми 12.1) картинка показує, до чого сходяться об'єми, і чи читається
регіон на карті. Старт: усі клітинки +9 °C (порода), стіни +9.

Права панель — ПОТОКИ ПОВІТРЯ: стрілка в кожній клітинці за напрямком зворотного потоку до камери гілки,
колір і товщина — скільки клітинок «зливають» повітря через цю клітинку (накопичений потік). Застійні зони
заштриховано, решітки — квадрати, камери — ромби.

Запуск: python gentemp.py 2031 pump [хвилин=120] [--stove]  (--stove: буржуйка в першій спальні, двері відчинені)
"""
import sys, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch, Rectangle

here = os.path.dirname(os.path.abspath(__file__))
argv = [a for a in sys.argv if not a.startswith("--")]
STOVE = "--stove" in sys.argv
T_MIN = int(argv[3]) if len(argv) > 3 else 120
sys.argv = argv[:3]  # genmap читає argv[1], argv[2]

# --- 1. Карта + вентиляція (той самий seed → та сама карта) ---
src = open(os.path.join(here, "genvent.py"), encoding="utf-8").read().split("# --- 7. Малюнок ---")[0]
g = {"__name__": "genvent", "sys": sys, "__file__": os.path.join(here, "genvent.py")}
exec(src, g)
N, maze, rooms, climate, PATH = g["N"], g["maze"], g["rooms"], g["climate"], g["PATH"]
gm = g["g"]  # простір імен genmap.py усередині genvent.py
start, exit_, SEED, STATE = g["start"], g["exit_"], g["SEED"], gm["STATE"]
grilles, chambers, ret_next, stagnant = g["grilles"], g["chambers"], g["ret_next"], set(g["stagnant"])
supply_temp, gen_region, CLIMATES = gm["supply_temp"], gm["gen_region"], g["CLIMATES"]
neighbors = g["neighbors"]
BRANCH_COLORS = g["BRANCH_COLORS"]
PALETTE_ = gm["PALETTE"]

WALL_K, DOOR_K, PASS_K = 0.01, 0.25, 0.25
T_ROCK = 9.0
path_cells = [(r, c) for r in range(N) for c in range(N) if maze[r][c] == PATH]

# --- 2. Джерела (кВт) ---
sources = {}
gen_room = next(((r0, c0, h, w) for r0, c0, h, w, t in rooms if t == "Генераторна"), None)
if gen_room and STATE != "off":
    r0, c0, h, w = gen_room
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            sources[(r, c)] = 6.0 / (h * w)          # 6 кВт на кімнату (12.9.1)
stove_cell = None
if STOVE:
    bed = next(((r0, c0, h, w) for r0, c0, h, w, t in rooms if t == "Спальня"), None)
    if bed:
        r0, c0, h, w = bed
        stove_cell = (r0 + h // 2, c0 + w // 2)
        sources[stove_cell] = sources.get(stove_cell, 0) + 4.0

# --- 3. Подача: температура в решітці за гілкою; потік = вентилятор 100 або природна тяга (12.7.0) ---
supply = {p: supply_temp(b) for p, (b, _) in grilles.items()}
FLOW = 1.0 if STATE != "off" else max(0.05, min(0.30, (10 + 1.0 * (T_ROCK - T_ROCK)) / 100))   # тяга 10 при секторі +9

# зворотний шлях: порядок від решіток до камери — використовуємо ret_next (крок 5б)
def k_between(a, b):
    return PASS_K  # обидві клітинки — проходи (сусіди беруться лише серед проходів)

Ta = {p: T_ROCK for p in path_cells}          # повітря
Tw = {p: T_ROCK for p in path_cells}          # стіни (усереднена стіна клітинки)
# бетонна стіна між проходом і стіною сектора: обмін через k=0,01 із породою моделюється кроком 4
# СТАБІЛЬНІСТЬ: сума коефіцієнтів на клітинку з 4 сусідами = 4×0,25 + 0,05 + 0,3 = 1,35 > 1, тому явна схема
# з кроком «1 хвилина» розбігається (перевірено: ±1000 °C за 120 хв). Хвилина ділиться на SUB підкроків із
# коефіцієнтами / SUB — так само, як 12.9.2 пропонує для локального оновлення (кожні 5 с з коефіцієнтами / 12).
SUB = 6
NB = {p: list(neighbors(*p)) for p in path_cells}
UP = {p: [q for q in NB[p] if ret_next.get(q) == p] for p in path_cells}
for minute in range(T_MIN * SUB):
    new = dict(Ta)
    for p in path_cells:
        t = Ta[p]
        dt = 0.4 * sources.get(p, 0.0)                                   # 1 джерела
        nb = NB[p]
        for n in nb:
            dt += PASS_K * (Ta[n] - t)                                    # 2 сусіди
        dt += (4 - len(nb)) * WALL_K * (Tw[p] - t)                        #   стіни-сусіди: слабкий обмін
        dt += 0.02 * (Tw[p] - t)                                          # 3 стіни (v1.2)
        if p in supply:
            dt += FLOW * 1.0 * (supply[p] - t)                            # 5 подача під решіткою × потік (v1.2)
        elif p in ret_next and p not in stagnant and UP[p]:
            up = UP[p]                                                    #   попередні за потоком
            dt += FLOW * 0.1 * (sum(Ta[q] for q in up) / len(up) - t)
        new[p] = t + dt / SUB
    for p in path_cells:
        Tw[p] += (0.02 * (Ta[p] - Tw[p]) + 0.005 * (T_ROCK - Tw[p])) / SUB  # 3, 4 (v1.2)
    Ta = new

# --- 4. Накопичений потік повітря по зворотному шляху ---
flow = collections.Counter()
for p in path_cells:
    q = p
    seen = 0
    while q in ret_next and seen < 10_000:
        q = ret_next[q]; flow[q] += 1; seen += 1

# --- 5. Малюнок ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 13.5))
X = lambda c: c + 0.5
Y = lambda r: N - 1 - r + 0.5
cmap, norm = plt.get_cmap("coolwarm"), mcolors.Normalize(vmin=-30, vmax=58)
for r in range(N):
    for c in range(N):
        if maze[r][c] != PATH:
            for ax in (ax1, ax2):
                ax.add_patch(Rectangle((c, N - 1 - r), 1, 1, color="#2c3e50"))
        else:
            ax1.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=cmap(norm(Ta[(r, c)]))))
for r0, c0, h, w, t in rooms:
    for ax in (ax1, ax2):
        ax.add_patch(Rectangle((c0, N - r0 - h), w, h, facecolor="none", edgecolor="black", lw=1.4))
    ax1.text(c0 + w / 2, N - r0 - h / 2, f"{t}\n{sum(Ta[(r, c)] for r in range(r0, r0+h) for c in range(c0, c0+w))/(h*w):+.0f}°",
             ha="center", va="center", fontsize=6, weight="bold")
    ax2.text(c0 + w / 2, N - r0 - h / 2 - 0.9, t, ha="center", va="center", fontsize=6)
# межі регіонів
for r in range(N):
    for c in range(N):
        if c + 1 < N and climate[r][c] != climate[r][c + 1]:
            ax1.plot([c + 1, c + 1], [N - 1 - r, N - r], color="#333", lw=0.8, ls=(0, (2, 2)))
        if r + 1 < N and climate[r][c] != climate[r + 1][c]:
            ax1.plot([c, c + 1], [N - 1 - r, N - 1 - r], color="#333", lw=0.8, ls=(0, (2, 2)))
for p, (b, kind) in grilles.items():
    ax1.plot(X(p[1]), Y(p[0]), "s", ms=5, color="white", mec="black", mew=0.8, zorder=6)
if stove_cell:
    ax1.plot(X(stove_cell[1]), Y(stove_cell[0]), "*", ms=16, color="#f39c12", mec="black", zorder=8)
# ізотерми
import numpy as np
Z = np.full((N, N), np.nan)
for (r, c), t in Ta.items():
    Z[r, c] = t
# ізотерми лише по проходах: стіни маскуються, тому контур не перетинає панелі
Zm = np.ma.masked_invalid(Z)
ax1.contour(np.arange(N) + 0.5, N - 1 - np.arange(N) + 0.5, Zm, levels=[-5, 12, 24, 30], colors="k", linewidths=0.6, alpha=0.6, corner_mask=True)

# права: потоки
fmax = max(flow.values()) if flow else 1
fcmap, fnorm = plt.get_cmap("viridis"), mcolors.LogNorm(vmin=1, vmax=fmax)
for (r, c), (pr, pc) in ret_next.items():
    f = flow.get((r, c), 1)
    col = fcmap(fnorm(max(f, 1)))
    ax2.add_patch(Rectangle((c, N - 1 - r), 1, 1, color=col, alpha=0.25))
    dr, dc = pr - r, pc - c
    ax2.arrow(X(c), Y(r), dc * 0.45, -dr * 0.45, width=0.02 + 0.08 * (f / fmax) ** 0.5, head_width=0.22 + 0.2 * (f / fmax) ** 0.5,
              head_length=0.18, length_includes_head=True, color=col, zorder=3)
for p in stagnant:
    ax2.add_patch(Rectangle((p[1], N - 1 - p[0]), 1, 1, facecolor="none", hatch="////", edgecolor="#555", lw=0))
for p, (b, kind) in grilles.items():
    ax2.plot(X(p[1]), Y(p[0]), "s", ms=7 if kind != "corridor" else 5, color=BRANCH_COLORS[b],
             mec="#c0392b" if kind == "spawn" else "black", mew=2 if kind == "spawn" else 0.8, zorder=7)
for i, ch in enumerate(chambers):
    ax2.plot(X(ch[1]), Y(ch[0]), "D", ms=15, color=BRANCH_COLORS[i], mec="black", mew=1.5, zorder=8)
    ax2.text(X(ch[1]), Y(ch[0]), str(i + 1), ha="center", va="center", fontsize=8, weight="bold", color="white", zorder=9)
for ax in (ax1, ax2):
    ax.add_patch(Rectangle((start[1], N - 1 - start[0]), 1, 1, color="#2ecc71", ec="black", lw=2, zorder=6))
    ax.add_patch(Rectangle((exit_[1], N - 1 - exit_[0]), 1, 1, color="#e74c3c", ec="black", lw=2, zorder=6))
    ax.set_xlim(0, N); ax.set_ylim(0, N); ax.set_aspect("equal"); ax.axis("off")

sb = plt.cm.ScalarMappable(cmap=cmap, norm=norm); sb.set_array([])
fig.colorbar(sb, ax=ax1, fraction=0.035, pad=0.01, label="T повітря, °C")
sf = plt.cm.ScalarMappable(cmap=fcmap, norm=fnorm); sf.set_array([])
fig.colorbar(sf, ax=ax2, fraction=0.035, pad=0.01, label="накопичений зворотний потік, клітинок")
sup_str = ", ".join(f"R{i+1} {supply_temp(i):+.0f}°" for i in range(5))
ax1.set_title(f"Температура повітря через {T_MIN} ігр. хв, seed={SEED}, стан «{STATE}», потік {int(FLOW*100)}"
              + (" + буржуйка 4 кВт у спальні" if stove_cell else "") + f"\nподача в решітки: {sup_str}; старт +9 °C; ізотерми 0/12/18/24/32",
              fontsize=11, linespacing=1.4)
ax2.set_title(f"Потоки повітря: приплив із решіток → проходами до камер гілок, seed={SEED}\n"
              f"{len(grilles)} решіток, {len(stagnant)} застійних клітинок (штриховка), макс. потік через клітинку {fmax}",
              fontsize=11, linespacing=1.4)
legend1 = [Patch(color="#2c3e50", label="Стіна"), plt.Line2D([], [], marker="s", color="white", mec="black", ls="", label="Решітка (подача)"),
           plt.Line2D([], [], color="k", lw=0.8, label="Ізотерми смуг 12.1")]
if stove_cell:
    legend1.append(plt.Line2D([], [], marker="*", color="#f39c12", mec="black", ms=12, ls="", label="Буржуйка 4 кВт"))
ax1.legend(handles=legend1, loc="upper center", bbox_to_anchor=(0.5, -0.005), ncol=4, fontsize=8, frameon=False)
legend2 = [Patch(color=BRANCH_COLORS[i], alpha=0.6, label=f"Гілка {i+1}: {CLIMATES[i][0]}") for i in range(5)] + \
          [Patch(facecolor="none", hatch="////", edgecolor="#555", label="Застійна зона"),
           plt.Line2D([], [], marker="D", color="#888", ms=10, ls="", mec="black", label="Камера гілки (витяг)"),
           plt.Line2D([], [], marker="s", color="#aaa", ms=7, ls="", mec="#c0392b", mew=2, label="Решітка-спавн")]
ax2.legend(handles=legend2, loc="upper center", bbox_to_anchor=(0.5, -0.005), ncol=3, fontsize=8, frameon=False)
plt.tight_layout()
out = os.path.join(here, f"temp_seed{SEED}_{STATE}{'_stove' if stove_cell else ''}.png")
plt.savefig(out, dpi=100)
BANDS = [(-99, -5, "Морозильна"), (-5, 12, "Холодна"), (12, 24, "Нейтральна"), (24, 30, "Тепла"), (30, 99, "Гаряча")]
band = lambda x: next(n for lo, hi, n in BANDS if lo <= x < hi)
corr_only = [p for p in path_cells if p not in supply]
for i in range(5):
    reg = [Ta[p] for p in corr_only if climate[p[0]][p[1]] == i]
    print(f"  R{i+1} проєкт {PALETTE_[i][0]} {PALETTE_[i][1]:+.0f}: коридори без решіток медіана {np.median(reg):+.1f} → смуга «{band(np.median(reg))}», p10/p90 {np.percentile(reg,10):+.1f}/{np.percentile(reg,90):+.1f}; під решітками {np.median([Ta[p] for p in supply if climate[p[0]][p[1]] == i]):+.1f}")
temps = sorted(Ta.values())
assert -45 <= temps[0] and temps[-1] <= 65, "схема розбіглася — збільшити SUB"
print(out, f"T min {temps[0]:+.1f} median {temps[len(temps)//2]:+.1f} max {temps[-1]:+.1f}",
      "| середня по регіонах:", ", ".join(f"R{i+1} {sum(Ta[p] for p in path_cells if climate[p[0]][p[1]]==i)/max(1,sum(1 for p in path_cells if climate[p[0]][p[1]]==i)):+.1f}" for i in range(5)))
