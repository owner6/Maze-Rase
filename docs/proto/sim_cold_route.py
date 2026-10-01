"""Інтеграція формули тіла 12.2 вздовж маршруту між станціями обігріву (12.9.8 п. 2).

Крок = 1 ігрова хвилина = 2 с реального часу. Швидкість ходьби 1,4 м/с, біг 4,5 м/с,
стаміна 100, витрата 12/с, відновлення 5/с при ходьбі, старт бігу лише при стаміні ≥ 10 (8.2).
Множники швидкості 12.3: 0,8 при T_тіла < 35, 0,5 при < 33. Клітинка 4 м.

Використання: python3 sim_cold_route.py [клітинок] [T_повітря] [clo] [walk|run]
Без аргументів друкує таблицю з 12.9.8.
"""
import sys

def integrate(cells, T_air, clo=2.0, wind=-3.0, mode="walk", T0=36.6):
    T_comf = 27 - 18 * clo
    dist, x, T, st, t, run_on, minT = cells * 4.0, 0.0, T0, 100.0, 0, False, T0
    while x < dist:
        mul = 1.0 if T >= 35 else (0.8 if T >= 33 else 0.5)
        if mode == "run":
            if not run_on and st >= 10: run_on = True
            if run_on and st <= 0: run_on = False
        if run_on:
            v, act, st = 4.5 * mul, 6, max(0.0, st - 24)
        else:
            v, act, st = 1.4 * mul, 2, min(100.0, st + 10)
        x += v * 2.0; t += 1
        T += 0.01 * (T_air + wind + act - T_comf) + 0.05 * (36.6 - T)
        minT = min(minT, T)
        if T < 30: break
    return t, T, minT

if __name__ == "__main__":
    if len(sys.argv) > 1:
        c, ta = int(sys.argv[1]), float(sys.argv[2])
        clo = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
        mode = sys.argv[4] if len(sys.argv) > 4 else "walk"
        t, T, m = integrate(c, ta, clo, mode=mode)
        print(f"{c} кл, {ta:+.0f} °C, clo {clo}, {mode}: {t} ігр. хв, T_кінець {T:.1f}, мін {m:.1f}")
    else:
        for ta, lab in ((-15, "коридор −15"), (-25, "коридор −25"), (-36, "під решіткою −36")):
            for mode in ("walk", "run"):
                t, T, m = integrate(40, ta, mode=mode)
                print(f"{lab:20s} 40 кл {mode:4s}: {t:3d} хв, T {T:.1f}")
        for mode in ("walk", "run"):
            ok = max(c for c in range(5, 200) if integrate(c, -36, mode=mode)[2] >= 33)
            print(f"макс клітинок при −36, clo 2,0, T ≥ 33, {mode}: {ok}")
