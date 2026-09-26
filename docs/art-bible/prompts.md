# Промпти для генерації референсів (Midjourney / SDXL / Flux / DALL-E)

Промпти англійською: генератори краще їх розуміють. Кожен промпт = базовий
префікс + опис + суфікс. Генерувати по 4 варіанти, лишати 1–2 найкращі,
зберігати як `moodboard/NN_категорія_опис.jpg` або `lighting/0N_*.jpg`.

## Базовий префікс і суфікс (вставляти в кожен промпт)

**PREFIX:**
```
Underground luxury survival bunker "Object 71", built 2031 for billionaires under the Carpathian mountains, modular wall panels on ceiling rails, 4 meter grid cells, 3.2 meter ceilings, exposed ventilation ducts and color-coded pipes overhead, three weeks after lockdown: expensive materials but worn, dusty, some panels shifted.
```

**SUFFIX:**
```
photorealistic, first-person eye level, 24mm lens, volumetric haze, muted palette of concrete grey, dark stainless steel and rust, cinematic, no people, no text, no watermark --ar 16:9
```

**Негатив (для SD/Flux):**
```
cartoon, anime, fantasy, clean white sci-fi, neon cyberpunk, daylight, windows, people, text, watermark, blurry
```

Для Midjourney додати `--style raw --v 6`. Для SDXL: steps 30, CFG 6.

---

## 1. Загальний вигляд коридору (3–5 шт.)

**01_corridor_straight**
```
PREFIX Long straight corridor of identical modular wall panels, visible seams every 4 meters, steel rail track along the ceiling, panel numbers stenciled on each module, one panel slightly out of alignment, fluorescent strip lights, SUFFIX
```

**02_corridor_junction**
```
PREFIX Four-way corridor intersection, one branch sealed by a wall panel that has just slid into place, scuff marks on the floor where the panel moved, dust in the air, SUFFIX
```

**03_corridor_dead_end**
```
PREFIX Dead-end corridor, a wall panel blocking what used to be a passage, scattered supply crate and a dropped flashlight on the floor, SUFFIX
```

**04_panel_closeup**
```
PREFIX Close-up of one modular wall panel on its rail mechanism: hydraulic joint, worn steel wheels, warning stripes, engraved serial number, brushed metal frame with a beige composite core, macro detail, SUFFIX
```

## 2. Реальні бункери (5–8 шт.)

**05_soviet_shelter**
```
Abandoned Soviet civil defense shelter, blast door, green painted walls peeling, ventilation filter units, hand-cranked air pump, Cyrillic stencils, photorealistic, first-person, cinematic, muted grey-green palette --ar 16:9
```

**06_swiss_shelter**
```
Swiss civil protection bunker interior, bunk beds stacked three high, grey concrete, orange emergency signage, steel doors with wheel locks, photorealistic, cinematic --ar 16:9
```

**07_datacenter_reference**
```
Server room corridor with rows of identical steel cabinets, cable trays overhead, raised floor tiles, cold blue-white light, photorealistic, first-person, cinematic --ar 16:9
```

**08_luxury_bunker**
```
Luxury survival condo inside a converted missile silo, marble and walnut finishes in a windowless concrete shell, fake window screens showing a forest, leather sofa, photorealistic, cinematic, slightly claustrophobic --ar 16:9
```

## 3. Кімнати MVP (по 1–2 на тип)

**09_room_start_box**
```
PREFIX Tiny 4 by 4 meter cell: a single bed with a thin mattress, a metal locker, a wall-mounted intercom, a sliding door half open onto a dark corridor, warm yellow bedside light, SUFFIX
```

**10_room_safe_room**
```
PREFIX Safe room with a heavy roller shutter door half raised, an automated supply vending cabinet with ammo and bandage slots, green "SAFE ZONE" ceiling lamp, scratched "no weapons" pictogram on the wall, SUFFIX
```

**11_room_bedroom**
```
PREFIX Dormitory-style bedroom, four bunk beds with premium but stained bedding, a wardrobe with winter coats, personal items left in a hurry, SUFFIX
```

**12_room_kitchen**
```
PREFIX Communal kitchen: induction stove, industrial fridge with a dead display, stainless sink, open cabinets with a few remaining cans, a kettle, water filter unit on the wall, SUFFIX
```

**13_room_storage**
```
PREFIX Storage room with steel shelving racks, plastic crates, stacked fuel canisters, labels in Ukrainian and English, one rack tipped over, SUFFIX
```

**14_room_medbay**
```
PREFIX Small medical bay: examination couch, glass medicine cabinet with some shelves emptied, sink, defibrillator on the wall, blood stain on the floor tiles, SUFFIX
```

**15_room_trading_post**
```
PREFIX Improvised trading post built inside a bunker room: counter made from a door on crates, goods laid out, a safe behind, a hand-painted price list, single hanging bulb, SUFFIX
```

**16_room_control**
```
PREFIX Sector control room: wall of monitors showing a shifting maze map, a terminal with a mechanical keyboard, the AI "Architect" status panel glowing amber, cables everywhere, SUFFIX
```

## 4. Знос і слід катастрофи (3–5 шт.)

**17_wear_rust**
```
Close-up of brushed stainless steel wall panel with rust streaks from a leaking pipe joint, water stains, peeling warning sticker, photorealistic macro, muted palette, no text --ar 16:9
```

**18_wear_gas_incident**
```
PREFIX Corridor after a gas leak: yellow chemical residue on the floor edges, discarded gas mask, overturned chair, emergency light still blinking, SUFFIX
```

**19_wear_infected_marks**
```
PREFIX Wall panel with claw scratches and dark smears at head height, torn ventilation grille, a trail leading into a dark side corridor, SUFFIX
```

## 5. Стеля і вентиляція (3–5 шт.)

**20_ceiling_pipes**
```
Looking straight up at a bunker ceiling: ventilation ducts, color-coded pipes (blue water, yellow gas, red fire), cable trays, a steel rail with a panel carriage, fluorescent fixtures, photorealistic, muted palette --ar 16:9
```

**21_vent_shaft_interior**
```
Inside a square steel ventilation duct, 1 meter wide, seams every 4 meters, a closed damper ahead with a small status LED, dust, faint light through a grille below, first-person crawling view, photorealistic --ar 16:9
```

**22_vent_grille_room**
```
PREFIX Ventilation grille in a room wall at floor level, partly unscrewed, cold air haze coming out, looking down the shaft into darkness, SUFFIX
```

## 6. Модульні стіни на рейках (3–5 шт.)

**23_rail_system_diagram**
```
Technical illustration, cutaway view of a bunker corridor showing modular wall panels sliding on ceiling and floor rails, hydraulic actuators, control conduit, isometric, blueprint style with beige and steel colors, labeled parts, clean line art --ar 16:9
```

**24_panel_in_motion**
```
PREFIX A wall panel caught mid-movement, sliding along its rail with a motion blur, sparks from the wheel, a siren light strobing red at the corridor end, SUFFIX
```

---

## Освітлення: 3 референси (`lighting/`)

Одна й та сама кімната (спальня) у трьох станах, щоб порівнювати лише світло.

**lighting/01_day**
```
PREFIX Dormitory bedroom with four bunk beds, standard daytime lighting: even cool-white fluorescent panels, soft shadows, all geometry clearly readable, calm, SUFFIX
```

**lighting/02_night_emergency**
```
PREFIX The same dormitory bedroom with four bunk beds during lockdown night mode: main lights off, only a red-orange emergency lamp above the door, deep shadows, a slowly rotating warning beacon, visibility reduced by haze, tense, SUFFIX
```

**lighting/03_safe_room**
```
PREFIX The same dormitory bedroom with four bunk beds converted into a safe zone: warm amber bedside lamps, a green "SAFE" indicator over the closed roller door, soft light pools on the beds, quiet and protective mood, SUFFIX
```

---

## Палітра

**palette_extract**
```
Color palette swatch sheet, 8 large rectangles with hex codes, derived from an underground worn luxury bunker: concrete grey, beige composite panel, dark stainless steel, rust orange, cool fluorescent white, emergency red-orange, safe-zone amber, exit red; flat design, white background --ar 16:9
```

Або без генерації: завантажити 5–8 найкращих зображень мудборду в
coolors.co / Adobe Color «Extract theme» і вписати HEX у `README.md`.

---

## Поради

- Один промпт = одна ідея. Не змішувати кімнату і коридор.
- Для консистентності в Midjourney: зробити 1 еталонний кадр коридору і
  використовувати його як `--sref` для решти.
- Спочатку генерувати коридор і панель (01–04), затвердити, потім усе інше.
- Зберігати seed/промпт у назві файлу або в `moodboard/README.md`, щоб можна
  було повторити.
