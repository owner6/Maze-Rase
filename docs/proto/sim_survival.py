"""Прототип виживання за нормативною специфікацією docs/spec/02-spec-mvp.md (переписано 2026-10-01).

Гравець-скрипт («розумний новачок»), NPC і заражені живуть кілька ігрових діб у секторі genmap/genvent <seed>.
Тік = 1 ігрова хвилина (2 с реального часу). Усе, що в специфікації задано в секундах реального часу,
згорнуто в хвилинні ймовірності або посекундні підцикли бою. Кожне правило підписано номером REQ.

Що моделюється:
  • Карта: genmap/genvent (REQ-MAZE, REQ-VENT-01..03); решітки noSpawn у стартовому боксі, сейф-кімнатах,
    спальнях, медпункті та на шлюзі (REQ-VENT-03); застій не моделюється (гази — лише з буржуйкою, якої немає).
  • Повітря: потік гілки = (100 з генератором) або тяга clamp(10 + (T_сер − 9); 5; 40) (REQ-VENT-04); шибер і заслінки
    гравець-скрипт не чіпає; f(потік) = clamp(потік/100; 0,25; 1) (REQ-POP-05).
  • Тепло: тепловий об'єм на регіон + окремий об'єм на кожну кімнату із зачиненими дверима (REQ-CLIMATE-01):
    ΔT = потік/100 × 0,04 × (T_подачі − T) + 0,01 × (9 − T) + k_дверей × 0,04 × Σ(T_сусід − T) + джерела, де T_подачі з таблиці
    режимів (REQ-VENT-07); генераторна +38 поки працює (REQ-HEAT-02); батарея +0,5 кВт у кімнату при котлі (REQ-HEAT-03);
    вітер під решіткою clamp((T − 21) × 0,3; −3; 3) (REQ-VENT-08).
  • Тіло: ΔT_тіла = 0,01 × (T_відчутна + активність − T_комфорт) + 0,05 × (36,6 − T_тіла), T_комфорт = 27 − 18 × clo,
    голод < 30 → +3 (REQ-CLIMATE-03); пороги REQ-CLIMATE-04 (гіпотермія II −1,5 HP/хв, III смерть за 10 хв,
    тепловий удар −1 HP/хв, спрага × 2 / × 3).
  • Потреби: −2,1 / −1,05 / −2,8 за год; множники біг × 2,5 / 1,6 / 1,5, спека > 28 спрага × 1,8, холод < 10 голод × 1,5;
    пороги 0 → HP −2 / −1 за хв; енергія 0 → непритомність 5 хв; регенерація +0,5 HP/год уві сні при ситості > 60
    (REQ-NEEDS-01). Їжа: консерви +35 / −3 спраги; пляшка 0,5 л +20, кран на кухні наповнює (REQ-NEEDS-02).
    Сон у ліжку +25/год, переривається шумом ≤ 15 м (REQ-NEEDS-03); безпечно лише за заблокованими дверима або в
    сейф-кімнаті, зачинені двері Блукач і Бігун відчиняють за 1 с, Набряклий ламає будь-які за 6 с (REQ-DOOR-02/03).
  • Одяг: костюм техніка clo 0,4; у спальні куртка пухова 0,9 + штани 0,5 → clo 1,4 (REQ-CLOTH-01); скрипт знімає
    куртку при T_тіла > 37,5 і надягає при < 36 (REQ-CLIMATE-04 пороги перегріву / охолодження).
  • Рух: ходьба 1,4 м/с = 21 кл/хв; біг 4,5 м/с зі стаміною 12/с і відновленням 5/с при ходьбі → у середньому ≈ 2,6 м/с
    = 39 кл/хв (REQ-MOVE-01/02); множники стану HP / голод / спрага / енергія / T_тіла перемножуються (REQ-MOVE-03).
  • Бій посекундно: ПМ-9 25 шкоди, 1 постр./с (темп 400/хв обмежено прицілюванням), влучання 70 % ≈ розкид 1,2°
    на 5–10 м з хедшотами; магазин 15, перезарядка 2,4 с; шум 60 м (REQ-COMBAT-02); ніж 35 за 0,45 с, стаміна −8,
    міцність −2 (REQ-COMBAT-03); укус: замах 0,6 с + кулдаун 1 с, p = 0,05 × 1,6 = 0,08 за замах, maxAttackers 1,
    блок ножем × 0,5 (REQ-COMBAT-06); шкода 15 / 20 / 30 (REQ-HEALTH-03); кровотеча від укусу 0,3 HP/с 60 с, бинт у
    аптечці (REQ-HEALTH-03, спрощено: аптечка +25 HP і зупиняє кровотечу).
  • Заражені: HP 50 / 75 / 125; швидкість 1,2 / 4,8 (8 с біг + 4 с крок → 3,6 сер.) / 0,9 м/с; зір 20 / 30 / 15 м;
    слух 15 / 25 / 10 м (REQ-ZOMB-01); патруль на перехресті 30 % зміна напрямку, не розвертається (REQ-ZOMB-03);
    пам'ять 8 с + пошук 15 с ≈ 1 хв розслідування (REQ-ZOMB-02); сейф-кімната і стартовий бокс — не бачать і не входять;
    перші 2 хв не рухаються (REQ-POP-09); старт 16 на решітках без noSpawn ≥ 12 кл від старту (REQ-POP-09).
  • Популяція: контакт — пара різних штамів в одній клітинці (≤ 1,5 м), обидва не в бою, монетка 50/50, народження на
    найближчій до пари решітці ≥ 25 м (6 кл) від гравця або смерть одного; кулдаун пари 30 с = 15 хв; при популяції ≤ 3
    народження вимкнене (REQ-POP-02/08); базове — progress += Δt × f / I_базовий на гілку, фаза в [0, 1), I medium 6 год,
    відкладення без втрати прогресу (REQ-POP-03/06); мутація раз на 10 хв при ≥ 2 (REQ-POP-07); ліміту популяції немає (DEC-083);
    защіпка шлюзу при дотику 0 назавжди (REQ-POP-08).
  • Спавнер (REQ-SPAWN-01, medium × 1,0): патрони 5–12 кожні 180–270 хв при популяції ≥ 1, лежать ≤ 4 год; аптечка
    240–360 хв у медпункті / спальні; ніж 70–130 / 120–210 хв на кухні; лом 60–110 / 90–150 хв на складі (інструменти лежать
    8 год); їжа і вода стартово 30 консервів і 60 пляшок на сектор (REQ-ECON-04 E) + 1 раз на 120–240 хв, ≤ 3 видимих;
    дизель 40 л каністрами по 5 л на складах і в генераторній + 1 каністра раз на 360–720 хв (REQ-HEAT-02, REQ-SPAWN-01).
    Сейф-кімната: +1 патрон за 2 хв стоячи, лише поки ролети активні 6–14 хв / пауза 10 (REQ-ROOMS-02).
  • Установка: бак 20 л спільний; генератор 1 л = 30 хв, запуск 5 с; котел 1 л = 45 хв, потребує насоса; насос — деталь
    із генераторної ломом 4 с (Q-03) (REQ-HEAT-02/03, REQ-QUEST-02). Стартовий інвентар (шафка): ПМ-9 з 15 + 10, ніж.
  • Смерть: режим «Стандарт» — через 6 год прокидається в найближчому ліжку з HP 40, потребами 50, T 36,6; інвентар на тілі
    24 год (скрипт по нього повертається) (REQ-NEEDS-04). SIM_DEATH=realism — ран завершується смертю.
  • NPC: 12 (1 торговець у сейф-кімнаті, 11 вцілілих у спальнях), беззбройні (REQ-NPC-03), потреби раз на 5 хв (REQ-NPC-01),
    Utility AI спрощено до пріоритетів: тікати > грітися (T < 35,5) > спати > пити > їсти (REQ-NPC-02); тікають до найближчої
    кімнати з дверима і зачиняють їх (50 %), заблокувати не можуть (лома нема) → Блукач відчиняє за 1 с.
  • Буржуйка (REQ-HEAT-01, REQ-VENT-14): стоїть у спальні, найближчій до старту (база гравця; припущення сценарію); дрова по 20 полін на
    складах (стек 20, REQ-ITEMS-01); поліно 20 хв на 4 кВт: +1,6 °C/хв на клітинку 51 м³, кімната гріється до +25, вище не гріє; розпал
    ×2 чаду в перші 3 хв. CO на кімнату за REQ-VENT-14: G = 0,03 м³/год, dt = 1/5 год; зачинені двері → приплив 0, щілина 8 м³/год
    у коридор із C ≈ 0; відчинені → кімната в коридорній зоні регіону (V = клітинки × 51, Q = 6 × потік × решітки регіону). Шкала
    CO_од = ppm/30; 60–89 HP −1/хв, ≥ 90 непритомність і смерть за 10 хв «чадний газ», уві сні без пробудження. Сценарій гравця за
    посібником 5.2: у холодній спальні (< 15 °C) запалити за заблокованими дверима, гріти до +22 або до CO 30, погасити, відчинити
    двері на 15 хв, потім заблокувати і спати.
  • NPC «Охолодитися» (дзеркально до «Грітися», DEC-080): при T_тіла > 37,5 іде в найближчу кімнату з дверима ≤ +24 °C і зачиняє їх.
  • Кімната — один тепловий об'єм: регіон визначає центр кімнати (DEC-080), а не клітинка, у якій стоїть персонаж.
  • DEC-081 (пакет балансу): патрони 360–540 хв, сейф-кімната +1/5 хв; стрибок Бігуна без замаху; пресет 0,03 × 2 (1 у дверях);
    гучний шум ≥ 40 м → переслідування всіх у радіусі; g(T_подачі) = 1,5 при ≥ +20; після котла гравець закриває вентилі гілок
    з T_проєкт ≥ +40 (оголошення № 13), NPC пам'ятають «регіон смертельний» 12 год; буржуйка — точкове джерело 1/(1 + d²);
    куртка розстібнута clo 0,95, пороги 38,0 / 36,0; респавн у ліжку без заражених у 30 м з ножем і водою; NPC підпирають двері 50 %.
  • DEC-082: NPC живуть у спальнях ≥ 8 кл від решіток без noSpawn (інакше в найдальшій); «Ховатися»: 2 год після зустрічі з зараженим
    NPC сидить за підпертими дверима, поки потреби ≥ 20 і T_тіла в нормі; на сон підпирає двері завжди.
  • Зброя заражених (REQ-ZOMB-01, REQ-SPAWN-02): Блукач бере ніж або пістолет (із тіла гравця), окремо патрони з кімнат і підлоги, перезаряджає (магазин 15, 2,4 с; DEC-084), Бігун — лише
    ніж, Набряклий нічого; озброєний кусає × 1,5; Блукач з пістолетом стріляє при зорі до 10 пострілів/хв з влучанням 0,25 (припущення для
    «розкиду 40 %»), у ближньому бою 1/с з 0,42, шкода 25, шум 60 м; убитий кидає зброю на клітинку, гравець підбирає. SIM_Z_ARMED=0 вимикає.
  • Архітектор: реконфігурація стін не моделюється (граф сталий), тривога не моделюється.

Запуск: python3 sim_survival.py <seed> [діб=3]; batch: python3 sim_survival.py --batch 2031 71 500 ... → survival_batch.png
Змінні середовища: SIM_DEATH=standard|realism, SIM_BASE_H (6), SIM_HIT (0,05), SIM_ATTACKERS (1), SIM_START (16),
SIM_CONTACT_STOP (3), SIM_FMIN (0,25), SIM_WORLD_ONLY=1 (без людей), SIM_STAY=1 (гравець не виходить: довгий ран із сном і буржуйкою), SIM_TRACE=1.
"""
import sys, os, math, random, collections
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__)); docs = os.path.dirname(here)
ENV = os.environ.get
DEATH_MODE = ENV("SIM_DEATH", "standard")
BASE_H = float(ENV("SIM_BASE_H", "6")); HIT = float(ENV("SIM_HIT", "0.03")); ATTACKERS = int(ENV("SIM_ATTACKERS", "2"))   # пресет DEC-081: 0,03 × 2
START_Z = int(ENV("SIM_START", "16")); CONTACT_STOP = int(ENV("SIM_CONTACT_STOP", "3")); F_MIN = float(ENV("SIM_FMIN", "0.25"))
CONTACT_CAP = int(ENV("SIM_CONTACT_CAP", "1000000000"))   # стеля контактних народжень: немає (DEC-083); абляція: 40
POP_MAX = int(ENV("SIM_POP_MAX", "1000000000"))
SPAWN_FAR = ENV("SIM_SPAWN_FAR", "0") == "1"
Z_ARMED = ENV("SIM_Z_ARMED", "1") == "1"   # заражені підбирають зброю (REQ-ZOMB-01, REQ-SPAWN-02); 0 = абляція
BODY_AMMO = int(ENV("SIM_BODY_AMMO", "0"))   # мінімум патронів на тілі гравця після смерті; 15 = сценарій «Блукач-стрілець»
Z_HIT_FAR = float(ENV("SIM_Z_HIT_FAR", "0.25")); Z_HIT_NEAR = float(ENV("SIM_Z_HIT_NEAR", "0.42"))   # влучання Блукача з пістолетом: розкид 40 % → припущення   # 1 = контактне народження на найдальшій решітці гілки (абляція гнізд)   # ліміту популяції немає (REQ-POP-10, DEC-083); абляція: 80
WORLD_ONLY = ENV("SIM_WORLD_ONLY", "0") == "1"; TRACE = ENV("SIM_TRACE", "0") == "1"
STAY = ENV("SIM_STAY", "0") == "1"   # 1 = гравець не виходить через шлюз і не полює: живе всі діб (сон, буржуйка, потреби)
T_ROCK = 9.0; CELL_M = 4.0


def run(SEED, DAYS, quiet=False, plot=True):
    # ---------------------------------------------------------------- карта
    sys.argv = [sys.argv[0], str(SEED), "off"]
    src = open(os.path.join(docs, "genvent.py"), encoding="utf-8").read().split("# --- 7. Малюнок ---")[0]
    g = {"__name__": "genvent", "sys": sys, "__file__": os.path.join(docs, "genvent.py")}
    exec(src, g)
    gm = g["g"]
    N, maze, rooms, PATH, climate = g["N"], g["maze"], g["rooms"], g["PATH"], g["climate"]
    start, exit_, grilles, doors_raw = g["start"], g["exit_"], g["grilles"], gm["doors"]
    setpoint, gen_region = gm["setpoint"], gm["gen_region"]
    chamber_of = {i: ch for (sr, sc, i), ch in zip(g["seeds"], g["chambers"])}   # камера гілки регіону (REQ-VENT-02)
    NREG = len(setpoint)
    rng = random.Random(SEED * 13 + 7)                      # потік sim (REQ-MAZE-02)
    cells = [(r, c) for r in range(N) for c in range(N) if maze[r][c] == PATH]
    passable = {p for p in cells}

    def nb(p):
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (p[0] + dr, p[1] + dc)
            if n in passable: yield n
    def bfs(srcs, limit=None):
        dist = {s: 0 for s in srcs}; q = collections.deque(srcs)
        while q:
            p = q.popleft()
            if limit is not None and dist[p] >= limit: continue
            for n in nb(p):
                if n not in dist: dist[n] = dist[p] + 1; q.append(n)
        return dist
    def md(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
    def meters(a, b): return math.hypot(a[0] - b[0], a[1] - b[1]) * CELL_M

    # кімнати, двері
    room_cells, room_type, room_of, door_cells, door_room = {}, {}, {}, {}, {}
    for i, (r0, c0, h, w, t) in enumerate(rooms):
        cc = [(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)]
        room_cells[i] = cc; room_type[i] = t
        for c in cc: room_of[c] = i
        door_cells[i] = list(doors_raw.get((r0, c0), []))
        for d in door_cells[i]: door_room[d] = i
    def rooms_of(t): return [i for i in room_cells if room_type[i] == t]
    def nearest_room(rooms_, cell): return min(rooms_, key=lambda i: dist_to[i].get(cell, 9999), default=None)
    center = {i: room_cells[i][len(room_cells[i]) // 2] for i in room_cells}
    gen_room = (rooms_of("Генераторна") or [None])[0]
    boiler_room = (rooms_of("Котельня") or [None])[0]
    kitchens, stores, beds, safes, meds = rooms_of("Кухня"), rooms_of("Склад"), rooms_of("Спальня"), rooms_of("Сейф-кімната"), rooms_of("Медпункт")
    dist_to = {i: bfs(room_cells[i]) for i in room_cells}
    dist_start, dist_exit = bfs([start]), bfs([exit_])
    # стан дверей: open / closed / locked (REQ-DOOR-01); ролети сейф-кімнати і стартовий бокс — непрохідні для заражених
    door_state = {i: "open" for i in room_cells}
    for i in safes: door_state[i] = "closed"
    def zombie_blocked(i, z):
        """Чи не може заражений увійти в кімнату i (REQ-DOOR-02, REQ-ZOMB-02)."""
        if i is None: return False
        if i in safes: return True
        st = door_state[i]
        if st == "open": return False
        if st == "closed": return False              # Блукач/Бігун відчиняють за 1 с; Набряклий ламає
        return z.kind != "bloat"                     # locked: лише Набряклий за 3 удари
    def z_opts(z, p):
        out = []
        for n in nb(p):
            i = room_of.get(n)
            if i is not None and i != room_of.get(p) and zombie_blocked(i, z): continue
            if n == start: continue
            out.append(n)
        return out

    # ---------------------------------------------------------------- установка і повітря
    plant = {"on": False, "tank": 0.0, "pump": False, "boiler": False, "blackouts": 0}
    valve_closed = {r: False for r in range(NREG)}            # вентиль калорифера (REQ-VENT-06): закритий → T_подачі +9
    def supply_T(reg):                               # таблиця режимів REQ-VENT-07
        if not plant["on"] or valve_closed[reg]: return T_ROCK
        if plant["boiler"]: return setpoint[reg]
        if plant["pump"]: return min(setpoint[reg], 15.0)
        return min(setpoint[reg], 15.0) if reg == gen_region else T_ROCK
    vol_T = {("reg", r): T_ROCK for r in range(NREG)}      # теплові об'єми (REQ-CLIMATE-01)
    for i in room_cells: vol_T[("room", i)] = T_ROCK
    flow_val = [10.0] * NREG
    def flow(reg=0): return flow_val[reg]
    def f_flow(reg=0): return max(F_MIN, min(1.0, flow(reg) / 100.0))
    def room_vol_separate(i): return door_state[i] != "open"
    def cell_T(p):
        i = room_of.get(p)
        if i == gen_room and plant["on"]: return 38.0        # REQ-HEAT-02 рекуперація
        if i is not None: return vol_T[("room", i)] + stove_off.get(p, 0.0)           # кімната — один об'єм (центр задає регіон, якщо двері відчинені)
        return vol_T[("reg", climate[p[0]][p[1]])]
    def felt_T(p):
        T = cell_T(p)
        if p in grilles and flow(climate[p[0]][p[1]]) > 0: T += max(-3.0, min(3.0, (T - 21) * 0.3))   # REQ-VENT-08
        return T
    reg_cells = collections.defaultdict(list)
    for p in cells: reg_cells[climate[p[0]][p[1]]].append(p)
    reg_of_room = {i: climate[center[i][0]][center[i][1]] for i in room_cells}
    def climate_tick():
        # потік (REQ-VENT-04)
        T_avg = np.mean([vol_T[("reg", r)] for r in range(NREG)])
        for r in range(NREG): flow_val[r] = 100.0 if plant["on"] else max(5.0, min(40.0, 10 + 1.0 * (T_avg - T_ROCK)))
        new = dict(vol_T)
        for r in range(NREG):
            T = vol_T[("reg", r)]
            d = flow(r) / 100 * 0.04 * (supply_T(r) - T) + 0.01 * (T_ROCK - T)
            new[("reg", r)] = T + d
        for i in room_cells:
            T = vol_T[("room", i)]; r = reg_of_room[i]; Treg = vol_T[("reg", r)]
            if not room_vol_separate(i): new[("room", i)] = new[("reg", r)]; continue
            k = 0.05                                                        # зачинені / заблоковані (REQ-VENT-09)
            d = flow(r) / 100 * 0.04 * (supply_T(r) - T) + 0.01 * (T_ROCK - T) + k * 0.04 * (Treg - T) * len(door_cells[i])
            if plant["boiler"]: d += 0.4 * 0.5 * 51 / (51 * len(room_cells[i]))   # батарея 0,5 кВт (REQ-HEAT-03)
            if stove["room"] == i and stove["burning"] > 0 and T < 25: d += np.mean([1.6 / (1 + dd * dd) for dd in stove_d.values()])   # середнє точкових внесків (DEC-081)
            new[("room", i)] = T + d
        vol_T.update(new)

    # ---------------------------------------------------------------- предмети, спавнер (REQ-SPAWN-01, REQ-ROOMS-02)
    items = collections.defaultdict(lambda: collections.Counter())   # room -> Counter(type)
    item_age = collections.defaultdict(list)                          # room -> [(type, t_spawn)]
    for i in kitchens: items[i]["food"] += 30 // max(1, len(kitchens)); items[i]["water"] += 60 // max(1, len(kitchens))
    diesel_rooms = stores + ([gen_room] if gen_room is not None else [])
    for k in range(8): items[diesel_rooms[k % len(diesel_rooms)]]["diesel"] += 1                  # 8 каністр × 5 л = 40 л
    for i in stores: items[i]["wood"] += 20                                                        # стек дров 20 (REQ-ITEMS-01)
    stove = {"room": nearest_room(beds, start) if beds else None, "burning": 0, "lit_for": 0}      # буржуйка в спальні-базі
    CO = collections.defaultdict(float)                                                            # ppm на кімнату (REQ-VENT-14)
    floor = collections.defaultdict(collections.Counter)                                            # предмети на клітинці (тіла, впущена зброя)
    stove_off = collections.defaultdict(float)                                                     # точковий внесок печі в клітинку (DEC-081)
    stove_d = {}
    if stove["room"] is not None:
        sc = center[stove["room"]]
        for c, d in bfs([sc], 3).items():
            if room_of.get(c) == stove["room"]: stove_d[c] = d
    def stove_tick():
        if stove["room"] is None: return
        Troom = vol_T[("room", stove["room"])]
        for c, d in stove_d.items():
            if stove["burning"] > 0:
                tgt = max(0.0, 25.0 - Troom) / (1 + d * d)
                stove_off[c] = min(tgt, stove_off[c] + 1.6 / (1 + d * d))
            else: stove_off[c] *= 0.96
    was_closed = {i: door_state[i] != "open" for i in room_cells}
    reg_grilles = collections.Counter(climate[p[0]][p[1]] for p in grilles)
    def co_units(i): return 0.0 if i is None else min(100.0, CO[i] / 30.0)
    def gas_tick():
        dt = 0.2
        for i in room_cells:
            G = 0.0
            if stove["room"] == i and stove["burning"] > 0: G = 0.03 * (2.0 if stove["lit_for"] <= 3 else 1.0)
            if G == 0 and CO[i] <= 0.01: continue
            V = 51.0 * len(room_cells[i]); C = CO[i]
            if door_state[i] == "open":
                r = reg_of_room[i]; Q = 6.0 * flow(r) * max(1, reg_grilles[r]); Vz = V + 51.0 * len(reg_cells[r])
                if was_closed[i]: C = C * V / Vz                                    # злиття зон: усереднення за масою (REQ-VENT-12)
                Ceq = G / Q * 1e6; C = Ceq + (C - Ceq) * math.exp(-Q * dt / Vz)
            else:
                C = C * math.exp(-8.0 * dt / V) + G * dt / V * 1e6                 # щілина 8 м³/год у чистий коридор (REQ-VENT-09)
            CO[i] = C
        for i in room_cells: was_closed[i] = door_state[i] != "open"
    spawn_tbl = {  # type: (перша, повтор, умова, кімнати, лежить хв)
        "ammo": ((360, 540), (360, 540), "pop", stores, 240), "medkit": ((240, 360), (240, 360), "pop", meds + beds, 240),
        "knife": ((70, 130), (120, 210), "always", kitchens, 480), "crowbar": ((60, 110), (90, 150), "always", stores, 480),
        "foodwater": ((120, 240), (120, 240), "always", kitchens + stores, 99999), "diesel": ((360, 720), (360, 720), "always", diesel_rooms, 99999),
    }
    spawn_timer = {k: rng.randint(*v[0]) for k, v in spawn_tbl.items()}
    def spawner_tick(t, pop):
        for k, (first, rep, cond, where, ttl) in spawn_tbl.items():
            if not where: continue
            spawn_timer[k] -= 1
            if spawn_timer[k] > 0: continue
            spawn_timer[k] = rng.randint(*rep)
            if cond == "pop" and pop < 1: continue
            room = rng.choice(where)
            if k == "ammo": items[room]["ammo"] += rng.randint(5, 12); item_age[room].append(("ammo", t)); stats["ammo_spawned"] += 1
            elif k == "foodwater":
                if sum(items[r]["food"] for r in where) < 3 + 30: items[room]["food"] += 1
                if sum(items[r]["water"] for r in where) < 3 + 60: items[room]["water"] += 1
            elif k == "diesel": items[room]["diesel"] += 1
            else:
                if sum(items[r][k] for r in where) == 0: items[room][k] += 1; item_age[room].append((k, t))
        for room in list(item_age):                              # зникнення (ресурси 4 год, інструменти 8 год)
            keep = []
            for kind, ts in item_age[room]:
                ttl = spawn_tbl[kind][4]
                if t - ts > ttl and items[room][kind] > 0: items[room][kind] -= (items[room][kind] if kind == "ammo" else 1); stats["despawned"] += 1
                elif t - ts <= ttl: keep.append((kind, ts))
            item_age[room] = keep

    stats = collections.Counter(); hist = collections.defaultdict(list); T_NOW = [0]

    noSpawn_rooms = set(beds + safes + meds)
    spawn_grilles = [p for p in grilles if room_of.get(p) not in noSpawn_rooms and p not in (start, exit_)]

    # ---------------------------------------------------------------- люди
    class Person:
        def __init__(s, cell, name, clo=0.4, npc=False):
            s.cell = cell; s.name = name; s.npc = npc; s.hp = 100.0; s.T = 36.6; s.thirst = s.hunger = s.energy = 100.0
            s.clo = clo; s.alive = True; s.sleeping = 0; s.cold_min = 0; s.cause = None; s.unconscious = 0
            s.inv = collections.Counter(); s.co_min = 0; s.ammo = 0; s.mag = 0; s.knife = 0; s.crowbar = 0; s.bleed = 0; s.stamina = 100.0
            s.log = []; s.deaths = 0; s.flee_streak = 0; s.body = None; s.died_at = None; s.sleep_total = 0; s.has_jacket = False
        def speed_mult(s):                                   # REQ-MOVE-03
            m = 1.0
            m *= 1.0 if s.hp >= 70 else 0.9 if s.hp >= 40 else 0.75 if s.hp >= 15 else 0.55
            if s.hunger < 20: m *= 0.85
            if s.thirst < 20: m *= 0.85
            if s.energy < 15: m *= 0.8
            if s.T < 33: m *= 0.5
            elif s.T < 35: m *= 0.8
            return m
        def can_run(s): return s.hp >= 15 and s.hunger >= 20 and s.thirst >= 20
        def steps(s, running):                                # клітинок за хвилину (REQ-MOVE-01/02)
            base = 39 if (running and s.can_run()) else 21
            return max(1, int(base * s.speed_mult()))
        def needs_tick(s, activity=0, running=False):
            env = felt_T(s.cell)
            th = 2.1 / 60 * (2.5 if running else 1) * (1.8 if env > 28 else 1) * (3 if s.T > 39.5 else 2 if s.T > 37.5 else 1)
            hu = 1.05 / 60 * (1.6 if running else 1) * (1.5 if env < 10 else 1)
            en = 2.8 / 60 * (1.5 if running else 1)
            if s.sleeping: en = -25 / 60
            s.thirst = max(0, min(100, s.thirst - th)); s.hunger = max(0, min(100, s.hunger - hu)); s.energy = max(0, min(100, s.energy - en))
            comfort = 27 - 18 * s.clo + (3 if s.hunger < 30 else 0)
            s.T += 0.01 * (env + activity - comfort) + 0.05 * (36.6 - s.T)
            if s.T < 33: s.hp -= 1.5                                            # гіпотермія II
            s.cold_min = s.cold_min + 1 if s.T < 30 else 0
            if s.T > 39.5: s.hp -= 1                                            # тепловий удар
            if s.thirst <= 0: s.hp -= 2
            if s.hunger <= 0: s.hp -= 1
            co = co_units(room_of.get(s.cell))
            if 60 <= co < 90: s.hp -= 1
            if co >= 90: s.co_min += 1; s.unconscious = max(s.unconscious, 1); s.sleeping = 0
            else: s.co_min = 0
            if s.co_min >= 10: s.die("чадний газ")
            if s.energy <= 0 and not s.sleeping and s.unconscious == 0: s.unconscious = 5; s.energy = 5
            if s.sleeping and s.hunger > 60: s.hp = min(100, s.hp + 0.5 / 60)
            if s.cold_min >= 10: s.die("гіпотермія III")
            elif s.hp <= 0: s.die("спрага" if s.thirst <= 0 else "голод" if s.hunger <= 0 else "гіпотермія II" if s.T < 33 else "тепловий удар" if s.T > 39.5 else "рани")
        def die(s, cause):
            if not s.alive: return
            s.alive = False; s.cause = cause; s.died_at = T_NOW[0]; s.deaths += 1
            stats["deaths_npc" if s.npc else "deaths_player"] += 1
            if not s.npc: s.log.append((T_NOW[0], f"смерть: {cause}"))
            elif TRACE: print(f"    † {s.name} {cause} t={T_NOW[0]/60:.1f}h cell={s.cell} room={room_type.get(room_of.get(s.cell))} door={door_state.get(room_of.get(s.cell))} T={s.T:.1f} flee={s.flee_streak}")
        def drink(s, room=None):
            if s.thirst >= 60: return False
            if room in kitchens: s.thirst = 100; return True                 # кран, пляшка наповнюється (REQ-NEEDS-02)
            if s.inv["water"] > 0: s.inv["water"] -= 1; s.thirst = min(100, s.thirst + 20); return True
            if room is not None and items[room]["water"] > 0: items[room]["water"] -= 1; s.thirst = min(100, s.thirst + 20); return True
            return False
        def eat(s, room=None):
            if s.hunger >= 60: return False
            if s.inv["food"] > 0: s.inv["food"] -= 1
            elif room is not None and items[room]["food"] > 0: items[room]["food"] -= 1
            else: return False
            s.hunger = min(100, s.hunger + 35); s.thirst = max(0, s.thirst - 3); return True

    player = Person(start, "гравець"); player.ammo = 10; player.mag = 15; player.knife = 100; player.visited = set(); player.has_pistol = True
    npcs = []
    if not WORLD_ONLY:
        # NPC у спальнях ≥ NPC_MIN_D клітинок по проходах від решіток без noSpawn, інакше найдальша (м'яке правило, DEC-082)
        NPC_MIN_D = int(ENV("SIM_NPC_MIN_D", "8"))
        dist_spawn = bfs(spawn_grilles)
        bed_d = {i: min(dist_spawn.get(c, 999) for c in room_cells[i]) for i in beds}
        far_beds = [i for i in beds if bed_d[i] >= NPC_MIN_D] or sorted(beds, key=lambda i: -bed_d[i])[:1]
        stats["npc_beds"] = f"{[bed_d[i] for i in far_beds]} з {sorted(bed_d.values())}"
        homes = (far_beds * 11)[:11]
        npcs = [Person(rng.choice(room_cells[i]), f"NPC{k}", clo=1.0, npc=True) for k, i in enumerate(homes)]
        if safes: npcs.append(Person(rng.choice(room_cells[safes[0]]), "торговець", clo=1.0, npc=True))
    else: player.alive = False; player.cause = "відсутній"; player.died_at = 0

    # ---------------------------------------------------------------- заражені
    KINDS, KIND_W = ["walker", "runner", "bloat"], [63, 27, 10]
    HPZ = {"walker": 50, "runner": 75, "bloat": 125}; DMG = {"walker": 15, "runner": 20, "bloat": 30}
    SPEED = {"walker": 18, "runner": 54, "bloat": 13}            # кл/хв: 1,2 / 3,6 (8 с біг + 4 с крок) / 0,9 м/с
    SIGHT = {"walker": 20, "runner": 30, "bloat": 15}; HEAR = {"walker": 15, "runner": 25, "bloat": 10}
    class Z:
        def __init__(s, cell, kind):
            s.cell = cell; s.kind = kind; s.hp = HPZ[kind]; s.alive = True; s.dir = None; s.target = None; s.memory = 0
            s.pairs = {}; s.in_combat = False; s.breaking = 0; s.loud = False; s.jumped = False; s.weapon = None; s.zammo = 0
    branch_grilles = collections.defaultdict(list)
    for gp in spawn_grilles: branch_grilles[grilles[gp][0]].append(gp)
    def new_kind(): return rng.choices(KINDS, KIND_W)[0]
    start_cells = [gp for gp in spawn_grilles if dist_start.get(gp, 0) >= 12]
    zs = [Z(rng.choice(start_cells), new_kind()) for _ in range(START_Z)]
    base_progress = {b: rng.random() for b in branch_grilles}
    noise = []                                                   # (cell, radius_m, minutes)
    airlock = {"open": False, "at": None}

    def far_from_player(gp): return not player.alive or meters(gp, player.cell) >= 25

    def z_pickup(z):
        if not Z_ARMED or z.kind == "bloat": return
        i = room_of.get(z.cell); src = [floor[z.cell]] + ([items[i]] if i is not None else [])
        for st in src:
            if z.kind == "walker" and z.weapon != "pistol" and st["pistol"] > 0:
                st["pistol"] -= 1; z.weapon = "pistol"; z.zammo += st["ammo"]; st["ammo"] = 0; stats["z_took_pistol"] += 1
            elif z.kind == "walker" and z.weapon == "pistol" and st["ammo"] > 0: z.zammo += st["ammo"]; st["ammo"] = 0; stats["z_took_ammo"] += 1
            elif z.weapon is None and st["knife"] > 0: st["knife"] -= 1; z.weapon = "knife"; stats["z_took_knife"] += 1
    def z_die(z):
        z.alive = False
        if z.weapon == "pistol": floor[z.cell]["pistol"] += 1; floor[z.cell]["ammo"] += z.zammo
        elif z.weapon == "knife": floor[z.cell]["knife"] += 1
        z.weapon = None; z.zammo = 0
    def patrol(z, steps):
        for _ in range(steps):
            opts = z_opts(z, z.cell)
            if not opts: return
            back = None if z.dir is None else (z.cell[0] - z.dir[0], z.cell[1] - z.dir[1])
            fwd = [n for n in opts if n != back] or opts
            ahead = (z.cell[0] + z.dir[0], z.cell[1] + z.dir[1]) if z.dir else None
            if ahead in fwd and len(fwd) > 1 and rng.random() >= 0.3: n = ahead     # 30 % змінити напрямок на перехресті
            else: n = rng.choice(fwd)
            z.dir = (n[0] - z.cell[0], n[1] - z.cell[1]); z.cell = n
    def z_move_to(z, target, steps):
        dm = bfs([target], 40)
        for _ in range(steps):
            opts = [n for n in z_opts(z, z.cell) if n in dm]
            if not opts: break
            best = min(opts, key=lambda c: dm[c])
            if dm[best] >= dm.get(z.cell, 9999): break
            z.cell = best
    def step_toward(person, dist_map, steps, avoid=None):
        """Крок по градієнту; avoid — клітинки, яких уникаємо; якщо з уникненням кроку немає — ідемо без нього (краще мороз, ніж стояти)."""
        start_cell = person.cell
        for _ in range(steps):
            opts = [c for c in nb(person.cell) if not avoid or c not in avoid]
            best = min(opts, key=lambda c: dist_map.get(c, 9999), default=person.cell)
            if dist_map.get(best, 9999) >= dist_map.get(person.cell, 9999): break
            person.cell = best
        if avoid and person.cell == start_cell: step_toward(person, dist_map, steps, None)

    # ---------------------------------------------------------------- бій (REQ-COMBAT-02/03/06, REQ-HEALTH-03)
    def fight(person, zombies, seconds=60, through_door=False):
        zombies = [z for z in zombies if z.alive]
        for z in zombies: z.in_combat = True
        shot = False; reload = 0; knife_cd = 0.0; swing = {}
        for z in [z for z in zombies if z.kind == "runner" and not getattr(z, "jumped", False)][:ATTACKERS]:   # стрибок 3 м без замаху (DEC-081)
            z.jumped = True
            p_j = HIT * 1.6 * (0.5 if (person.knife > 0 and person.ammo + person.mag == 0 and not person.npc) else 1.0)
            stats["jumps"] += 1
            if rng.random() < p_j: person.hp -= DMG["runner"] + 3; stats["bites"] += 1
        if person.hp <= 0: person.die("укуси"); return False
        for sec in range(seconds):
            zombies = [z for z in zombies if z.alive]
            if not zombies or not person.alive: break
            tgt = min(zombies, key=lambda z: z.hp)
            if reload > 0: reload -= 1
            elif person.ammo + person.mag > 0 and not person.npc and getattr(person, "has_pistol", True):
                if person.mag == 0: person.mag = min(15, person.ammo); person.ammo -= person.mag; reload = 2; continue
                person.mag -= 1; stats["shots"] += 1
                if rng.random() < 0.7: tgt.hp -= 25 * (4 if rng.random() < 0.15 else 1)      # 15 % хедшотів
                if not shot: noise.append((person.cell, 60, 2)); shot = True
            elif person.knife > 0 and person.stamina >= 8:
                for _ in range(2):                                                          # 2 удари/с по 0,45 с
                    if person.stamina < 8: break
                    person.stamina -= 8; person.knife -= 2
                    if rng.random() < 0.65: tgt.hp -= 35
            person.stamina = min(100, person.stamina + 8)
            if tgt.hp <= 0: z_die(tgt); stats["kills"] += 1; stats["kills_npc" if person.npc else "kills_player"] += 1; stats["kills_armed"] += 1 if tgt.weapon else 0
            # укуси: замах 0,6 + кулдаун 1 с → раз на 1,6 с, p = HIT × 1,6; блок ножем × 0,5 (без патронів)
            attackers = [z for z in zombies if z.alive][:1 if through_door else ATTACKERS]
            for z in attackers:
                swing[id(z)] = swing.get(id(z), 0) + 1
                if swing[id(z)] < 1.6: continue
                swing[id(z)] = 0
                p = HIT * 1.6 * (0.5 if (person.knife > 0 and person.ammo + person.mag == 0 and not person.npc) else 1.0)
                if rng.random() < p:
                    person.hp -= DMG[z.kind] * (1.5 if z.weapon else 1.0) + 3; stats["bites"] += 1   # укус (озброєний × 1,5) + кровотеча (REQ-HEALTH-03)
            for z in [z for z in zombies if z.alive and z.kind == "walker" and z.weapon == "pistol" and z.zammo > 0][:1]:   # Блукач із пістолетом: 1 постріл/с, магазин 15, перезарядка 2,4 с
                z.zmag = getattr(z, "zmag", 0)
                if z.zmag == 0:
                    z.zreload = getattr(z, "zreload", 0) + 1
                    if z.zreload >= 3: z.zmag = min(15, z.zammo); z.zreload = 0
                    continue
                z.zmag -= 1; z.zammo -= 1; stats["z_shots"] += 1
                if rng.random() < Z_HIT_NEAR: person.hp -= 25; stats["z_hits"] += 1
            if person.hp <= 0: person.die("укуси"); break
            if not person.npc and person.hp < 25 and sec >= 3: person.flee_now = True; break
        for z in zombies: z.in_combat = False; z.jumped = False
        return person.alive

    # сейф-кімната: ролети активні 6–14 хв, пауза 10, перша активація через 3–10 хв; активність лише при популяції ≥ 1 (REQ-ROOMS-02)
    safe_sched = []; _t = rng.randint(3, 10)
    while _t < DAYS * 1440 + 20: _on = rng.randint(6, 14); safe_sched.append((_t, _t + _on)); _t += _on + 10
    def safe_active(t): return sum(z.alive for z in zs) >= 1 and any(a <= t < b for a, b in safe_sched if a <= t)

    # ---------------------------------------------------------------- гравець-скрипт
    p = player; p.goal = None; p.flee_now = False; p.wait = 0; p.lock_timer = 0; p.part = False; p.respawn_at = None
    def nearest(rooms_, cell): return min(rooms_, key=lambda i: dist_to[i].get(cell, 9999), default=None)
    def pick_up(room, t):
        got = []
        it = items[room]
        if it["ammo"] > 0 and p.ammo < 60: p.ammo += it["ammo"]; it["ammo"] = 0; got.append("патрони")
        if it["medkit"] > 0 and p.inv["medkit"] < 2: p.inv["medkit"] += 1; it["medkit"] -= 1; got.append("аптечка")
        if it["knife"] > 0 and p.knife < 40: p.knife = 100; it["knife"] -= 1; got.append("ніж")
        if it["crowbar"] > 0 and p.crowbar <= 0: p.crowbar = 100; it["crowbar"] -= 1; got.append("лом")
        if it["diesel"] > 0 and p.inv["diesel"] < 4: n = min(4 - p.inv["diesel"], it["diesel"]); p.inv["diesel"] += n; it["diesel"] -= n; got.append(f"дизель {n * 5} л")
        if it["wood"] > 0 and p.inv["wood"] < 10: n = min(10 - p.inv["wood"], it["wood"]); p.inv["wood"] += n; it["wood"] -= n; got.append(f"дрова {n}")
        for k, cap in (("water", 3), ("food", 3)):
            n = min(cap - p.inv[k], it[k])
            if n > 0: p.inv[k] += n; it[k] -= n
        if room in beds and not p.has_jacket: p.has_jacket = True; p.clo = 1.4; got.append("куртка+штани")
        if got: p.log.append((t, ", ".join(got)))
        item_age[room] = [(k, ts) for k, ts in item_age[room] if items[room][k] > 0]

    def player_tick(t):
        if not p.alive:
            if DEATH_MODE == "standard" and p.respawn_at is not None and t >= p.respawn_at:        # REQ-NEEDS-04
                safe_beds = [b for b in beds if all(meters(center[b], z.cell) > 30 for z in zs if z.alive)]   # без заражених у 30 м (DEC-081)
                bed = nearest(safe_beds, p.body) if safe_beds else None
                p.cell = center[bed] if bed is not None else start
                p.alive = True; p.hp = 40; p.thirst = p.hunger = p.energy = 50; p.T = 36.6; p.bleed = 0; p.cold_min = 0
                if p.has_pistol: floor[p.body]["pistol"] += 1; p.has_pistol = False
                floor[p.body]["ammo"] += max(p.ammo + p.mag, BODY_AMMO)             # на тілі лишається ≥ BODY_AMMO патронів (сценарій)
                if p.knife > 0: floor[p.body]["knife"] += 1
                p.body_inv = (0, 0, 0, p.crowbar, dict(p.inv), p.clo); p.ammo = p.mag = 0; p.knife = p.crowbar = 0; p.inv = collections.Counter(); p.clo = 0.4
                p.body_until = t + 24 * 60; p.respawn_at = None; p.knife = 100; p.inv["water"] = 1; p.log.append((t, "респавн")); stats["respawns"] += 1   # ніж і вода в шафці (DEC-081)
            return
        here_room = room_of.get(p.cell)
        if p.unconscious > 0: p.unconscious -= 1; p.needs_tick(); return
        in_safe = here_room in safes or p.cell == start
        adj = [z for z in zs if z.alive and md(z.cell, p.cell) <= 1]
        near_z = [] if in_safe else adj
        # загроза при вході: заражений у дверях зачиненої кімнати (locked — лише Набряклий)
        if here_room is not None and not in_safe and door_state[here_room] != "open":
            near_z = [z for z in adj if z.cell in room_cells[here_room] or z.kind == "bloat" or door_state[here_room] == "closed"]
        if p.sleeping > 0:
            p.stove_state = None
            loud = any(n for n in noise if meters(n[0], p.cell) <= 15)
            if near_z or loud: p.sleeping = 0
            else:
                p.sleeping -= 1; p.sleep_total += 1; p.needs_tick(); return
        fl = floor[p.cell]
        if fl["pistol"] > 0 and not getattr(p, "has_pistol", True): fl["pistol"] -= 1; p.has_pistol = True; p.log.append((t, "пістолет"))
        if fl["ammo"] > 0 and p.ammo < 60: p.ammo += fl["ammo"]; fl["ammo"] = 0
        if fl["knife"] > 0 and p.knife < 40: p.knife = 100; fl["knife"] -= 1
        if p.thirst < 40: p.drink(here_room)
        if p.hunger < 40: p.eat(here_room)
        if p.hp < 50 and p.inv["medkit"] > 0: p.inv["medkit"] -= 1; p.hp = min(100, p.hp + 25); p.bleed = 0; p.log.append((t, "аптечка"))
        if not near_z: p.flee_streak = 0
        if near_z:
            others = [i for i in safes + beds if i != here_room]
            safe = nearest(others, p.cell)
            can_flee = safe is not None and dist_to[safe].get(p.cell, 99) <= (12 if any(z.kind == "runner" for z in near_z) else 35)
            dps = 0.7 * 25 * 1.45 if p.ammo + p.mag > 0 else 2 * 0.65 * 35
            exp_dmg = sum(z.hp for z in near_z) / dps / 1.6 * HIT * 1.6 * max(DMG[z.kind] for z in near_z)
            unarmed = p.ammo + p.mag == 0 and p.knife <= 0
            if can_flee and (unarmed or (exp_dmg > p.hp - 15 and p.flee_streak < 30)):
                step_toward(p, dist_to[safe], p.steps(True)); stats["flees"] += 1; p.flee_streak += 1; p.needs_tick(6, True)
                if here_room is not None and room_of.get(p.cell) == safe: door_state[safe] = "locked" if p.crowbar > 0 else "closed"
                return
            p.flee_now = False; fight(p, near_z, through_door=(here_room is not None and door_state[here_room] != "open" and not any(z.cell in room_cells[here_room] for z in near_z)))
            if p.alive and p.flee_now and can_flee: step_toward(p, dist_to[safe], p.steps(True)); stats["flees"] += 1
            p.needs_tick(2); return
        # у кімнаті: підбір, установка
        if here_room is not None:
            p.visited.add(here_room); pick_up(here_room, t)
            if here_room == gen_room:
                if p.inv["diesel"] > 0 and plant["tank"] <= 15: n = min(p.inv["diesel"], int((20 - plant["tank"]) // 5) or 1); plant["tank"] = min(20, plant["tank"] + 5 * n); p.inv["diesel"] -= n; p.log.append((t, f"заправка {5 * n} л"))
                if plant["tank"] > 0 and not plant["on"]: plant["on"] = True; p.log.append((t, "генератор")); noise.append((p.cell, 40, 1))
                if not p.part and p.crowbar > 0: p.part = True; p.crowbar -= 25; p.log.append((t, "деталь насоса"))
            if here_room == boiler_room and p.part and not plant["pump"] and plant["on"]:
                plant["pump"] = True; p.log.append((t, "насос")); stats["pump_at"] = t
            if here_room == boiler_room and plant["pump"] and plant["on"] and not plant["boiler"] and plant["tank"] > 6:
                plant["boiler"] = True; p.log.append((t, "котел"))
                p.valve_todo = [r for r in range(NREG) if setpoint[r] >= 40 and not valve_closed[r]]   # оголошення № 13 (DEC-081)
        for r in list(getattr(p, "valve_todo", [])):
            if p.cell == chamber_of[r]: valve_closed[r] = True; p.valve_todo.remove(r); p.log.append((t, f"вентиль гілки {r+1} закрито"))
            if here_room in safes and p.ammo + p.mag < 30 and t % 5 == 0 and safe_active(t): p.ammo += 1   # REQ-ROOMS-02 (DEC-081: 1 за 5 хв)
        if p.has_jacket:
            if p.T > 38.0 and p.clo > 1.0: p.clo = 0.95; stats["jacket_toggles"] += 1         # розстібнув: 0,9 × 0,5 + 0,5 (DEC-081)
            elif p.T > 38.5 and p.clo > 0.5: p.clo = 0.4; stats["jacket_toggles"] += 1
            elif p.T < 36.0 and p.clo < 1.4: p.clo = 1.4 if p.clo > 0.5 else 0.95; stats["jacket_toggles"] += 1
        # ціль
        target = None; running = False
        if getattr(p, "body_until", 0) > t and p.body is not None and p.ammo + p.mag == 0:              # по інвентар на тілі
            if p.cell == p.body or md(p.cell, p.body) == 0:
                _, _, _, p.crowbar, inv, p.clo = p.body_inv; p.inv.update(inv); p.body_until = 0; p.log.append((t, "забрав речі з тіла" + ("" if floor[p.body]["pistol"] else " (пістолет забрав заражений)")))
            else: step_toward(p, bfs([p.body]), p.steps(False)); p.needs_tick(2); return
        if here_room is not None and co_units(here_room) >= 30 and door_state[here_room] != "open":
            door_state[here_room] = "open"; stove["burning"] = 0; p.log.append((t, f"чад {co_units(here_room):.0f}: відчинив двері"))   # іконка «повітря»
        if p.energy < 25 and beds:
            b = stove["room"] if (stove["room"] is not None and dist_to[stove["room"]].get(p.cell, 999) <= 60) else nearest(beds, p.cell)
            if here_room == b:
                st = getattr(p, "stove_state", None)
                if st is None and b == stove["room"] and cell_T(center[b]) < 15 and p.inv["wood"] > 0:
                    door_state[b] = "locked" if p.crowbar > 0 else "closed"; p.inv["wood"] -= 1; stove["burning"] = 20; stove["lit_for"] = 0
                    p.stove_state = "heating"; p.log.append((t, "буржуйка")); p.needs_tick(); return
                if st == "heating":
                    if stove["burning"] == 0 and p.inv["wood"] > 0 and cell_T(center[b]) < 22: p.inv["wood"] -= 1; stove["burning"] = 20
                    if cell_T(center[b]) >= 22 or co_units(b) >= 30 or (stove["burning"] == 0 and p.inv["wood"] == 0):
                        stove["burning"] = 0; door_state[b] = "open"; p.stove_state = "venting"; p.vent_left = 15; p.log.append((t, f"прогрів {cell_T(center[b]):.0f}°, CO {co_units(b):.0f}, провітрює"))
                    p.needs_tick(); return
                if st == "venting":
                    p.vent_left -= 1
                    if p.vent_left > 0: p.needs_tick(); return
                    p.stove_state = None
                door_state[b] = "locked" if p.crowbar > 0 else "closed"
                if p.crowbar > 0: p.crowbar -= 5
                p.sleeping = 360; p.needs_tick(); return
            target = b
        elif p.inv["wood"] == 0 and stove["room"] is not None and any(items[i]["wood"] > 0 for i in stores) and p.energy < 45:
            target = nearest([i for i in stores if items[i]["wood"] > 0], p.cell)
        elif p.thirst < 40 and p.inv["water"] == 0: target = nearest(kitchens, p.cell)
        elif p.hunger < 40 and p.inv["food"] == 0: target = nearest([i for i in kitchens + stores if items[i]["food"] > 0], p.cell)
        elif not p.has_jacket and p.T < 36.2 and beds: target = nearest(beds, p.cell)
        elif p.T < 35.5: target = max(beds + kitchens + safes, key=lambda i: (cell_T(center[i]), -dist_to[i].get(p.cell, 9999)))
        elif p.T > 38.5:
            target = min([i for i in room_cells if i != gen_room], key=lambda i: (cell_T(center[i]) > 24, dist_to[i].get(p.cell, 9999)))
        elif p.hp < 40 and any(items[i]["medkit"] > 0 for i in meds + beds): target = nearest([i for i in meds + beds if items[i]["medkit"] > 0], p.cell)
        elif p.ammo + p.mag < 10 and any(items[i]["ammo"] > 0 for i in stores): target = nearest([i for i in stores if items[i]["ammo"] > 0], p.cell)
        elif p.ammo + p.mag < 5 and safes and sum(z.alive for z in zs) >= 1: target = nearest(safes, p.cell)
        elif p.knife < 30 and any(items[i]["knife"] > 0 for i in kitchens): target = nearest([i for i in kitchens if items[i]["knife"] > 0], p.cell)
        elif p.crowbar <= 0 and any(items[i]["crowbar"] > 0 for i in stores): target = nearest([i for i in stores if items[i]["crowbar"] > 0], p.cell)
        elif p.inv["diesel"] == 0 and plant["tank"] < 5 and any(items[i]["diesel"] > 0 for i in diesel_rooms): target = nearest([i for i in diesel_rooms if items[i]["diesel"] > 0], p.cell)
        elif airlock["open"] and not STAY:
            if p.cell == exit_: stats["exit_at"] = t; return "exit"
            step_toward(p, dist_exit, p.steps(False)); p.needs_tick(2); return
        elif not STAY and 0 < sum(z.alive for z in zs) <= 5 and p.ammo + p.mag >= 6 and p.hp >= 40 and len(p.visited) >= len(room_cells) // 2:
            zc = min((z for z in zs if z.alive), key=lambda z: md(z.cell, p.cell)).cell       # зачистка останніх (посібник: «коли лишається 3 — добити»)
            step_toward(p, bfs([zc]), p.steps(False)); stats["hunt_min"] += 1; p.needs_tick(2); return
        elif getattr(p, "valve_todo", []):
            r = min(p.valve_todo, key=lambda r: bfs([chamber_of[r]]).get(p.cell, 9999))
            step_toward(p, bfs([chamber_of[r]]), p.steps(False)); p.needs_tick(2); return
        elif p.inv["diesel"] > 0 and gen_room is not None and plant["tank"] <= 15: target = gen_room
        elif not p.part and p.crowbar > 0 and gen_room is not None: target = gen_room
        elif p.part and not plant["pump"] and plant["on"] and boiler_room is not None: target = boiler_room
        elif plant["pump"] and not plant["boiler"] and plant["on"] and plant["tank"] > 6 and boiler_room is not None: target = boiler_room
        else:
            unvisited = [i for i in room_cells if i not in p.visited]
            target = nearest(unvisited, p.cell) if unvisited else rng.choice(list(room_cells))
        if target is not None and here_room == target: target = None
        if target is not None and cell_T(center[target]) < -5 and p.T < 36 and target not in (gen_room, boiler_room): target = None
        if target is not None:
            cold = {c for c in cells if cell_T(c) < -5 and room_of.get(c) != target} if cell_T(p.cell) >= -5 else set()
            if p.T > 37.5: cold |= {c for c in cells if cell_T(c) > 32 and room_of.get(c) != target and cell_T(p.cell) <= 32}
            if here_room is not None and door_state[here_room] != "open": door_state[here_room] = "open"   # виходячи, двері лишає відчиненими
            step_toward(p, dist_to[target], p.steps(False), cold)
        p.needs_tick(2 if target is not None else 0)
        if TRACE and t % 20 == 0:
            print(f"  t={t/60:5.1f}h cell={p.cell} target={room_type.get(target) if target is not None else None}@{center[target] if target is not None else None} d={dist_to[target].get(p.cell) if target is not None else None} room={room_type.get(here_room)} T_cell={cell_T(p.cell):+.0f} T={p.T:.1f} HP={p.hp:.0f} th={p.thirst:.0f} hu={p.hunger:.0f} en={p.energy:.0f} ammo={p.ammo+p.mag} z={sum(z.alive for z in zs)} plant={plant['on']}/{plant['pump']}/{plant['boiler']} tank={plant['tank']:.1f}")

    # ---------------------------------------------------------------- NPC (REQ-NPC-01/02/03)
    deadly = {}                                                            # регіон → до якого часу вважається смертельним (DEC-081)
    def ok_room(i, t): return deadly.get(reg_of_room[i], -1) < t
    def npc_tick(n_, t):
        if not n_.alive: return
        hr = room_of.get(n_.cell)
        if n_.T > 38.5 or n_.T < 34: deadly[climate[n_.cell[0]][n_.cell[1]]] = t + 12 * 60
        FEAR = int(ENV("SIM_FEAR_MIN", "120"))                                  # «Ховатися» (DEC-082): 2 год після зустрічі не виходить
        in_safe = hr in safes
        adj = [z for z in zs if z.alive and md(z.cell, n_.cell) <= 1]
        near_z = [] if in_safe else adj
        if hr is not None and door_state[hr] != "open" and not in_safe:
            near_z = [z for z in adj if z.cell in room_cells[hr] or z.kind == "bloat" or door_state[hr] == "closed"]
        if near_z:
            n_.sleeping = 0; n_.fear_until = t + FEAR
            # «Тікати» (REQ-NPC-02): беззбройний вцілілий тікає, поки є куди — у сейф-кімнату (заражені не входять), інакше в
            # найближчу кімнату з дверима і зачиняє їх (50 %); укус навздогін 30 % за хвилину контакту
            zin = {room_of.get(z.cell) for z in zs if z.alive}
            cands = [i for i in safes + beds if i != hr and i not in zin]          # кімната з дверима без заражених усередині (DEC-081)
            safe = nearest(safes, n_.cell)
            room = safe if (safe is not None and dist_to[safe].get(n_.cell, 999) <= 25) else nearest(cands, n_.cell)
            if room is not None and dist_to[room].get(n_.cell, 999) > 0:
                before = n_.cell; step_toward(n_, dist_to[room], n_.steps(True)); n_.flee_streak += 1; stats["npc_flees"] += 1
                if room_of.get(n_.cell) == room and room not in safes and room not in zin and door_state[room] != "locked" and rng.random() < 0.5: door_state[room] = "locked"; stats["npc_barricades"] += 1   # підпер меблями (DEC-081)
                if rng.random() < (0.3 if n_.cell != before else 0.6): n_.hp -= 18
                if n_.hp <= 0: n_.die("укуси")
                n_.needs_tick(6, True); return
            fight(n_, near_z, 30); n_.needs_tick(); return
        n_.flee_streak = 0
        hiding = getattr(n_, "fear_until", -1) > t and hr is not None and hr not in safes and door_state[hr] == "locked"
        if getattr(n_, "fear_until", -1) > t and hr is not None and hr not in safes and door_state[hr] != "locked" and not any(z.alive and room_of.get(z.cell) == hr for z in zs):
            door_state[hr] = "locked"; stats["npc_barricades"] += 1; hiding = True   # підпирає двері, щойно опинився в кімнаті
        if hiding and min(n_.thirst, n_.hunger) >= 20 and n_.T >= 34 and n_.T <= 38.5:
            if hr is not None: n_.drink(hr); n_.eat(hr)
            if n_.sleeping > 0: n_.sleeping -= 1
            elif n_.energy < 25: n_.sleeping = 360
            stats["npc_hiding"] += 1; n_.needs_tick(); return
        if n_.sleeping > 0:
            if any(meters(x[0], n_.cell) <= 15 for x in noise): n_.sleeping = 0
            else: n_.sleeping -= 1; n_.needs_tick(); return
        if hr is not None: n_.drink(hr); n_.eat(hr)
        cold_all = {c for c in cells if cell_T(c) < -5} if cell_T(n_.cell) >= -5 else None
        if n_.T < 35.5:
            warm = max(beds + kitchens + safes, key=lambda i: (ok_room(i, t), min(cell_T(center[i]), 24), -dist_to[i].get(n_.cell, 9999)))
            if hr != warm: step_toward(n_, dist_to[warm], n_.steps(False), cold_all)
            elif door_state[warm] == "open": door_state[warm] = "closed"
        elif n_.T > 37.5:                                                   # «Охолодитися» (DEC-080): найближча кімната з дверима ≤ +24
            cool = min(beds + kitchens + safes, key=lambda i: (cell_T(center[i]) > 24, not ok_room(i, t), dist_to[i].get(n_.cell, 9999)))
            if hr != cool: step_toward(n_, dist_to[cool], n_.steps(False), cold_all)
            elif door_state[cool] == "open" and cool not in safes: door_state[cool] = "closed"
            stats["npc_cooling"] += 1
        elif n_.energy < 25 and beds:
            b = max(beds, key=lambda i: (ok_room(i, t), cell_T(center[i]) >= 5, -dist_to[i].get(n_.cell, 9999)))
            if hr == b:
                n_.sleeping = 360
                if not any(z.alive and room_of.get(z.cell) == b for z in zs): door_state[b] = "locked"; stats["npc_barricades"] += 1   # підпирає на сон (DEC-082)
            else: step_toward(n_, dist_to[b], n_.steps(False), cold_all)
        elif n_.thirst < 50: step_toward(n_, dist_to[nearest(kitchens, n_.cell)], n_.steps(False), cold_all) if kitchens else None
        elif n_.hunger < 50:
            c = nearest([i for i in kitchens + stores if items[i]["food"] > 0], n_.cell)
            if c is not None: step_toward(n_, dist_to[c], n_.steps(False), cold_all)
        n_.needs_tick(2)

    # ---------------------------------------------------------------- головний цикл
    MIN = DAYS * 1440; result = None
    for t in range(MIN):
        T_NOW[0] = t
        climate_tick()
        if stove["burning"] > 0: stove["burning"] -= 1; stove["lit_for"] += 1; stats["stove_min"] += 1
        else: stove["lit_for"] = 0
        stove_tick()
        gas_tick()
        if TRACE and stove["room"] is not None and (stove["burning"] > 0 or CO[stove["room"]] > 1) and t % 10 == 0:
            print(f"      піч t={t/60:.2f} burn={stove['burning']} door={door_state[stove['room']]} T_room={cell_T(center[stove['room']]):.1f} CO={co_units(stove['room']):.1f} player_in={room_of.get(player.cell)==stove['room']} wood={player.inv['wood']} flow={flow(reg_of_room[stove['room']]):.0f} supply={supply_T(reg_of_room[stove['room']]):.0f}")
        pop = sum(z.alive for z in zs)
        spawner_tick(t, pop)
        if plant["on"]:
            plant["tank"] -= 1 / 30 + (1 / 45 if plant["boiler"] else 0)
            if plant["tank"] <= 0: plant["tank"] = 0; plant["on"] = plant["boiler"] = False; plant["blackouts"] += 1
        if player_tick(t) == "exit": result = "exit"; break
        if not player.alive and player.respawn_at is None and DEATH_MODE == "standard" and player.cause != "відсутній":
            player.body = player.cell; player.respawn_at = t + 360
        if not player.alive and DEATH_MODE == "realism": break
        for n_ in npcs:
            if t % 5 == 0 or n_.sleeping or any(md(z.cell, n_.cell) <= 1 for z in zs if z.alive): npc_tick(n_, t)
            elif n_.alive: n_.needs_tick(0)
        # заражені
        alive_z = [z for z in zs if z.alive]
        if t >= 2:
            for z in alive_z:
                if z.in_combat: continue
                seen = None
                if player.alive and room_of.get(player.cell) not in safes and player.cell != start and meters(z.cell, player.cell) <= SIGHT[z.kind]:
                    d = bfs([z.cell], int(SIGHT[z.kind] / CELL_M) + 1)
                    if player.cell in d: seen = player.cell
                if seen is None:
                    for n_ in npcs:
                        if n_.alive and room_of.get(n_.cell) not in safes and meters(z.cell, n_.cell) <= SIGHT[z.kind] and (room_of.get(n_.cell) is None or door_state[room_of[n_.cell]] == "open" or room_of.get(n_.cell) == room_of.get(z.cell)):
                            if n_.cell in bfs([z.cell], int(SIGHT[z.kind] / CELL_M) + 1): seen = n_.cell; break
                if seen is not None:
                    z.target = seen; z.memory = 1
                    if z.kind == "walker" and z.weapon == "pistol" and z.zammo > 0 and md(z.cell, seen) >= 2:
                        victim = player if seen == player.cell else next((n_ for n_ in npcs if n_.alive and n_.cell == seen), None)
                        for _ in range(min(10, z.zammo)):                                   # поза боєм: ≤ 10 постр./хв, перезарядка в межах хвилини
                            z.zammo -= 1; stats["z_shots"] += 1
                            if victim is not None and rng.random() < Z_HIT_FAR: victim.hp -= 25; stats["z_hits"] += 1
                        noise.append((z.cell, 60, 2))
                        if victim is not None and victim.hp <= 0: victim.die("постріл зараженого")
                else:
                    heard = [x for x in noise if meters(x[0], z.cell) <= min(x[1], HEAR[z.kind] if x[1] < 60 else 60)]
                    if heard: z.target = heard[0][0]; z.memory = 1; z.loud = heard[0][1] >= 40
                if z.target is not None:
                    z_move_to(z, z.target, SPEED[z.kind])
                    if z.cell == z.target: z.memory -= 1                       # пам'ять 8 с + пошук лише після прибуття
                    elif z.loud: pass                                          # гучний шум: переслідує до точки (DEC-081)
                    else: z.memory -= 1
                    if z.memory <= 0: z.target = None; z.loud = False
                else: patrol(z, SPEED[z.kind])
                z_pickup(z)
        # популяція (REQ-POP-02/03/07/08/10)
        pop = len(alive_z)
        births_ok = CONTACT_STOP < pop < CONTACT_CAP
        for b, gps in branch_grilles.items():
            base_progress[b] += f_flow(b) * (1.5 if supply_T(b) >= 20 else 1.0) / (BASE_H * 60)   # g(T_подачі) = 1,5 при ≥ +20 (DEC-081)
            if base_progress[b] >= 1.0 and sum(z.alive for z in zs) < POP_MAX:
                cand = [gp for gp in gps if far_from_player(gp)]
                if not cand: stats["base_deferred"] += 1; continue
                base_progress[b] -= 1.0; zs.append(Z(rng.choice(cand), new_kind())); stats["base_births"] += 1
        pos = collections.defaultdict(list)
        for z in alive_z: pos[z.cell].append(z)
        for z in alive_z:
            if not z.alive or z.in_combat: continue
            for o in pos[z.cell]:
                if o is z or not o.alive or o.kind == z.kind or o.in_combat or z.pairs.get(id(o), -999) > t - 15: continue
                z.pairs[id(o)] = t; o.pairs[id(z)] = t
                if rng.random() < 0.5:
                    if births_ok and sum(x.alive for x in zs) < POP_MAX:
                        cand = [gp for gp in spawn_grilles if far_from_player(gp)]
                        if cand and SPAWN_FAR:                                              # абляція: найдальша решітка своєї гілки від пари
                            own = [gp for gp in cand if grilles[gp][0] == climate[z.cell[0]][z.cell[1]]] or cand
                            zs.append(Z(max(own, key=lambda gp: md(gp, z.cell)), new_kind())); stats["births"] += 1
                        elif cand: zs.append(Z(min(cand, key=lambda gp: md(gp, z.cell)), new_kind())); stats["births"] += 1
                else: z_die(o if rng.random() < 0.5 else z); stats["contact_deaths"] += 1
                break
        if t % 10 == 0:
            live = [z for z in zs if z.alive]
            if len(live) >= 2:
                z = rng.choice(live); nk = rng.choice([k for k in KINDS if k != z.kind])
                z.hp = max(1, round(z.hp / HPZ[z.kind] * HPZ[nk])); z.kind = nk; stats["mutations"] += 1
                if z.weapon == "pistol" and nk != "walker":                              # зброя при мутації (REQ-POP-07, DEC-084)
                    floor[z.cell]["pistol"] += 1; floor[z.cell]["ammo"] += z.zammo; z.weapon = None; z.zammo = 0; z.zmag = 0; stats["z_dropped"] += 1
                elif z.weapon == "knife" and nk == "bloat": floor[z.cell]["knife"] += 1; z.weapon = None; stats["z_dropped"] += 1
        noise = [(c, r, m - 1) for c, r, m in noise if m > 1]
        za = sum(z.alive for z in zs); stats["peak"] = max(stats["peak"], za)
        if za == 0 and not airlock["open"]: airlock["open"] = True; airlock["at"] = t; stats["zero_at"] = t
        if t % 20 == 0:
            hist["t"].append(t / 60); hist["hp"].append(player.hp if player.alive else 0); hist["thirst"].append(player.thirst)
            hist["hunger"].append(player.hunger); hist["energy"].append(player.energy); hist["T"].append(player.T if player.alive else np.nan)
            hist["Tcell"].append(cell_T(player.cell)); hist["npc"].append(sum(n_.alive for n_ in npcs)); hist["z"].append(za)
            hist["ammo"].append(player.ammo + player.mag); hist["plant"].append(3 if plant["boiler"] else 2 if plant["pump"] and plant["on"] else 1 if plant["on"] else 0)
            hist["Treg"].append([vol_T[("reg", r)] for r in range(NREG)]); hist["flow"].append(flow(0))
            live = [z for z in zs if z.alive]                                   # скупчення: кластери за відстанню ≤ 2 кл (8 м)
            seen = set(); best = 0
            for z in live:
                if id(z) in seen: continue
                stack = [z]; seen.add(id(z)); n = 0
                while stack:
                    a = stack.pop(); n += 1
                    for b in live:
                        if id(b) not in seen and md(a.cell, b.cell) <= 2: seen.add(id(b)); stack.append(b)
                best = max(best, n)
            hist["cluster"].append(best); hist["cluster_share"].append(best / len(live) if live else 0)
            hist["branches"].append(len({climate[z.cell[0]][z.cell[1]] for z in live}))
            hist["co"].append(co_units(stove["room"])); hist["Tstove"].append(cell_T(center[stove["room"]]) if stove["room"] is not None else np.nan)
    end_t = t
    # ---------------------------------------------------------------- підсумок
    alive_npc = sum(n_.alive for n_ in npcs)
    if result == "exit": outcome = f"ВИЙШОВ через шлюз на {stats['exit_at']/60:.1f} год"
    elif player.alive: outcome = "живий"
    elif DEATH_MODE == "standard" and player.cause != "відсутній": outcome = f"мертвий (чекає респавну), {player.cause}"
    else: outcome = f"загинув: {player.cause} на {player.died_at/60:.1f} год"
    summary = dict(seed=SEED, outcome=outcome, exit_at=stats.get("exit_at"), zero_at=stats.get("zero_at"), deaths=stats["deaths_player"],
                   npc_alive=alive_npc, npc_total=len(npcs), peak=stats["peak"], z_end=sum(z.alive for z in zs), base=stats["base_births"],
                   contact=stats["births"], kills=stats["kills_player"], hp=player.hp, pump=stats.get("pump_at"), causes=collections.Counter(n_.cause for n_ in npcs if not n_.alive),
                   player_causes=[b for a, b in player.log if b.startswith("смерть")], cl_max=max(hist["cluster"]), z_knife=stats["z_took_knife"], z_pistol=stats["z_took_pistol"], z_shots=stats["z_shots"], z_hits=stats["z_hits"], cl_med=float(np.median(hist["cluster"])), cl_share=float(np.median(hist["cluster_share"])), br_med=float(np.median(hist["branches"])), stove_min=stats["stove_min"], co_max=max(hist["co"]) if hist["co"] else 0, jumps=stats["jumps"])
    if not quiet:
        print(f"seed {SEED}, {DAYS} діб: гравець {outcome}; смертей {stats['deaths_player']} (HP {player.hp:.0f}, T {player.T:.1f}, спрага {player.thirst:.0f}, голод {player.hunger:.0f}, енергія {player.energy:.0f}, clo {player.clo}); патрони {player.ammo + player.mag}, ніж {player.knife}, лом {player.crowbar}")
        print(f"  установка: on={plant['on']} насос={plant['pump']} котел={plant['boiler']} бак {plant['tank']:.1f} л, відключень {plant['blackouts']}; T регіонів {[round(vol_T[('reg', r)]) for r in range(NREG)]}, потік {flow(0):.0f}")
        print(f"  події гравця ({stats['jacket_toggles']} перевдягань куртки): {[(round(a/60,1), b) for a, b in player.log]}")
        print(f"  NPC живі {alive_npc}/{len(npcs)}; причини: {dict(summary['causes'])}; спальні NPC (відстань до решіток) {stats['npc_beds']}")
        print(f"  заражені: {summary['z_end']} (старт {START_Z}), контактних {stats['births']}, базових {stats['base_births']}, мутацій {stats['mutations']}, смертей від контакту {stats['contact_deaths']}, убито гравцем {stats['kills_player']}, укусів {stats['bites']}, пострілів {stats['shots']}, втеч {stats['flees']}, пік {stats['peak']}")
        print(f"  DEC-081: стрибків Бігуна {stats['jumps']}, підпертих дверей NPC {stats['npc_barricades']}, ховались {stats['npc_hiding']} хв, вентилі закриті {[r+1 for r in range(NREG) if valve_closed[r]]}, смертельні регіони NPC {[r+1 for r in deadly]}")
        print(f"  зброя заражених: узяли ніж {stats['z_took_knife']}, пістолет {stats['z_took_pistol']}, патрони {stats['z_took_ammo']} разів; пострілів {stats['z_shots']}, влучань {stats['z_hits']}; озброєних убито {stats['kills_armed']}, зброї випало при мутації {stats['z_dropped']}; у гравця пістолет {player.has_pistol}")
        print(f"  скупчення: найбільший кластер (≤ 8 м) медіана {np.median(hist['cluster']):.0f}, максимум {max(hist['cluster'])}; частка популяції в ньому медіана {np.median(hist['cluster_share']) * 100:.0f} %; зайнято гілок медіана {np.median(hist['branches']):.0f} з {NREG}")
        print(f"  буржуйка: горіла {stats['stove_min']} хв, макс CO у базі {max(hist['co']) if hist['co'] else 0:.0f} од., дров у гравця {player.inv['wood']}; NPC охолоджувались {stats['npc_cooling']} хв")
        print(f"  защіпка шлюзу: {'%.1f год' % (stats['zero_at']/60) if 'zero_at' in stats else 'ні'}; патронів коробок {stats['ammo_spawned']}, зникло предметів {stats['despawned']}")
    if plot:
        fig, ax = plt.subplots(2, 2, figsize=(16, 9))
        tt = hist["t"]
        a = ax[0][0]; a.plot(tt, hist["hp"], "r", label="HP"); a.plot(tt, hist["thirst"], "b", label="спрага"); a.plot(tt, hist["hunger"], "g", label="голод"); a.plot(tt, hist["energy"], "m", label="енергія")
        a.plot(tt, hist["co"], color="brown", ls="--", label="CO у спальні-базі (од.)"); a.axhline(60, color="brown", lw=0.5, ls=":"); a.axhline(90, color="brown", lw=0.5, ls=":")
        a.set_title("Гравець (потреби, HP) і чад у спальні-базі"); a.set_xlabel("ігр. год"); a.legend(loc="lower left", fontsize=8); a.set_ylim(0, 102)
        for a_, b_ in player.log:
            if b_.startswith("смерть"): a.axvline(a_ / 60, color="k", ls=":", lw=0.8)
        a = ax[0][1]; a.plot(tt, hist["T"], "k", label="T тіла"); a.axhline(35, color="orange", lw=0.8); a.axhline(33, color="r", lw=0.8); a.axhline(37.5, color="orange", lw=0.8)
        a.set_title("T тіла гравця / T клітинки / режим установки"); a.set_xlabel("ігр. год"); a.set_ylim(28, 42)
        a2 = a.twinx(); a2.plot(tt, hist["Tcell"], color="c", alpha=0.6, label="T клітинки"); a2.plot(tt, hist["Tstove"], color="brown", alpha=0.5, lw=0.8, label="T спальні-бази"); a2.step(tt, [x * 10 for x in hist["plant"]], "g", where="post", alpha=0.5, label="установка ×10"); a2.set_ylim(-35, 65)
        a.legend(loc="upper left", fontsize=8); a2.legend(loc="upper right", fontsize=8)
        a = ax[1][0]; a.plot(tt, hist["z"], "r", label="заражені"); a.plot(tt, hist["npc"], "b", label="NPC живі"); a.plot(tt, hist["ammo"], color="gray", ls="--", label="патрони гравця")
        if airlock["open"]: a.axvline(airlock["at"] / 60, color="g", ls="--", label="защіпка шлюзу")
        a.set_title("Популяції"); a.set_xlabel("ігр. год"); a.legend(fontsize=8)
        a = ax[1][1]; TR = np.array(hist["Treg"])
        for r in range(NREG): a.plot(tt, TR[:, r], label=f"регіон {r+1} (проєкт {setpoint[r]:+.0f})")
        a.set_title("Теплові об'єми регіонів (REQ-VENT-07)"); a.set_xlabel("ігр. год"); a.legend(fontsize=7)
        fig.suptitle(f"Виживання за спец. v1.2 — seed {SEED}, {DAYS} діб: гравець {outcome}; смертей {stats['deaths_player']}, NPC {alive_npc}/{len(npcs)}, заражених {summary['z_end']} (пік {stats['peak']})", fontsize=11)
        plt.tight_layout(); out = os.path.join(here, f"survival_seed{SEED}{'_stay' if STAY else ''}.png"); plt.savefig(out, dpi=100); plt.close(fig)
        if not quiet: print(" ", out)
    return summary, hist


def batch(seeds, days):
    rows = []; hists = {}
    for s in seeds:
        summ, h = run(s, days, quiet=True, plot=True); rows.append(summ); hists[s] = h
        print(f"seed {s:5d}: {summ['outcome']:45s} смертей {summ['deaths']} NPC {summ['npc_alive']}/{summ['npc_total']} пік {summ['peak']:2d} кінець {summ['z_end']:2d} баз {summ['base']:2d} конт {summ['contact']:3d} убив {summ['kills']:3d} стриб {summ['jumps']:2d} ножів {summ['z_knife']:2d} піст {summ['z_pistol']} постр {summ['z_shots']:3d}/{summ['z_hits']:2d} защіпка {('%.1f' % (summ['zero_at']/60)) if summ['zero_at'] is not None else '—'}")
    n = len(rows)
    exits = [r for r in rows if r["exit_at"] is not None]; zero = [r["zero_at"] / 60 for r in rows if r["zero_at"] is not None]
    deaths = [r["deaths"] for r in rows]; npc = [r["npc_alive"] / max(1, r["npc_total"]) for r in rows]
    print(f"\n{n} seed × {days} діб: вихід {len(exits)}/{n}; защіпка {len(zero)}/{n} (медіана {np.median(zero) if zero else float('nan'):.1f} год); "
          f"смертей гравця медіана {np.median(deaths):.0f} (0 смертей: {sum(d == 0 for d in deaths)}/{n}); NPC медіана {np.median(npc) * 100:.0f} %; "
          f"пік популяції медіана {np.median([r['peak'] for r in rows]):.0f}; кінець медіана {np.median([r['z_end'] for r in rows]):.0f}")
    print(f"  скупчення: найбільший кластер медіана по seed {np.median([r['cl_med'] for r in rows]):.0f} (макс по seed медіана {np.median([r['cl_max'] for r in rows]):.0f}, абсолютний {max(r['cl_max'] for r in rows)}); частка популяції в найбільшому кластері медіана {np.median([r['cl_share'] for r in rows]) * 100:.0f} %; зайнято гілок медіана {np.median([r['br_med'] for r in rows]):.0f}")
    print(f"  зброя заражених: ножів узято всього {sum(r['z_knife'] for r in rows)}, пістолет {sum(r['z_pistol'] for r in rows)} разів на {sum(1 for r in rows if r['z_pistol'])} seed; пострілів {sum(r['z_shots'] for r in rows)}, влучань {sum(r['z_hits'] for r in rows)}")
    causes = collections.Counter(c for r in rows for c in r["player_causes"]); print("  причини смертей гравця:", dict(causes))
    ncauses = collections.Counter(); [ncauses.update(r["causes"]) for r in rows]; print("  причини смертей NPC:", dict(ncauses))
    fig, ax = plt.subplots(2, 2, figsize=(16, 9))
    for s, h in hists.items():
        ax[0][0].plot(h["t"], h["z"], alpha=0.6, lw=1); ax[0][1].plot(h["t"], h["npc"], alpha=0.6, lw=1)
        ax[1][0].plot(h["t"], h["hp"], alpha=0.6, lw=1); ax[1][1].plot(h["t"], h["ammo"], alpha=0.6, lw=1)
    ax[0][0].set_title(f"Заражені по seed (медіана піку {np.median([r['peak'] for r in rows]):.0f})"); ax[0][1].set_title("NPC живі по seed")
    ax[1][0].set_title(f"HP гравця по seed (0 = мертвий до респавну; медіана смертей {np.median(deaths):.0f})"); ax[1][1].set_title("Патрони гравця по seed")
    for a in ax.flat: a.set_xlabel("ігр. год")
    fig.suptitle(f"Батч {n} seed × {days} діб за спец. v1.2: вихід {len(exits)}/{n}, защіпка {len(zero)}/{n}, NPC медіана {np.median(npc) * 100:.0f} %", fontsize=12)
    plt.tight_layout(); out = os.path.join(here, "survival_batch.png"); plt.savefig(out, dpi=100); print(" ", out)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        days = int(os.environ.get("SIM_DAYS", "3")); batch([int(a) for a in args[1:]] or [2031, 71, 500, 42, 7, 99, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15], days)
    else:
        SEED = int(args[0]) if args else 2031; DAYS = int(args[1]) if len(args) > 1 else 3
        run(SEED, DAYS)
