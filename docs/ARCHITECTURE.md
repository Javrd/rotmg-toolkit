# Arquitectura

Scrapea la wiki de RealmEye para tres cosas independientes y las sirve
en una única página HTML estática (en inglés, como el propio juego) con
tres secciones navegables: "Where to Find Stat Potions" (qué pociones
suelta cada mazmorra/boss de mundo abierto y si están garantizadas),
"Equipment Compare" (comparador visual de dos piezas de equipo del mismo
grupo de clases) y "Fame Checklist" (checklist de los bonus de fama por
colección de mazmorras).

No hay pip/venv disponibles en este NUC (sin `python3-venv`, sin acceso
`sudo` sin contraseña), así que todo está escrito en stdlib puro
(`urllib`, `re`, `json`) — nada de `requests`/`bs4`.

## Componentes

- **`scraper.py`** — todo el scraping:
  - `get_dungeon_list()`: parsea `/wiki/dungeons` y saca `{name, href,
    category}` para las ~84 mazmorras listadas. Las que esa tabla lista
    sin thumbnail (Oryx's Castle, que se entra desde el reino y no por
    portal) rellenan el icono con `get_portal_icon(href)`, que busca en
    la página propia de la mazmorra el `<img ... title="X Portal">` — la
    única imagen de esa página que seguro es el portal y no un jefe, un
    mapa o una captura. Es **solo** un fallback: donde la lista trae
    icono, ese manda, porque unas pocas páginas muestran una variante
    animada `.gif` o arte distinto del que ya usa el resto del sitio.
  - `scrape_dungeon(name, href)`: para una mazmorra, parsea la sección
    "Drops of Interest" y las secciones cuyo título contiene "boss"
    (jefe principal) o "treasure room" + "boss" (jefe de sala del
    tesoro). Cruza cada ítem-poción con la página del enemigo concreto
    que lo suelta, mirando su tabla "Drops" en busca del marcador
    `<sup><abbr>G...</abbr></sup>` (garantizado, a veces con condición
    tipo "G - 2" o "G - ?").
  - `fetch()` cachea cada página HTML en `data/cache/` (nombre = URL con
    caracteres no alfanuméricos sustituidos por `_`) para poder
    re-ejecutar sin volver a golpear la red.
  - `run_all(out_path)` recorre todas las mazmorras y escribe
    `data/dungeon_potions.json`.
  - `scrape_fame_collections()` / `run_fame(out_path)`: la tabla
    "Dungeon Collection" de `/wiki/fame-bonuses` (ver más abajo).
  - Uso: `python3 scraper.py` (prueba con Woodland Labyrinth),
    `python3 scraper.py all data/dungeon_potions.json` (todas),
    `python3 scraper.py biomes data/biome_potions.json` o
    `python3 scraper.py fame data/fame_bonuses.json`.

- **`build_html.py`** — lee `data/dungeon_potions.json` +
  `data/biome_potions.json` + `data/fame_bonuses.json` + (recuento de)
  `data/equipment.json` y genera `index.html`: una sola página con un
  `<nav>` de tres pestañas de nivel superior ("Where to Find Stat
  Potions" / "Equipment Compare" / "Fame Checklist").
  La primera reusa el buscador/filtro de tipo/toggle "guaranteed only" y
  las sub-pestañas Dungeons / Open-World Biomes de siempre. En la
  pestaña Dungeons cada sección es una categoría de mazmorra
  (`build_dungeon_sections`) y cada tarjeta es una mazmorra. En la
  pestaña Open-World Biomes cada sección es un bioma (ordenados
  Rookie→Adept→Veteran→Seasonal, `build_biome_sections`) y cada tarjeta
  es un enemigo individual de ese bioma (`render_biome_monster_card`,
  icono más grande vía `card-icon-lg` que el de una mazmorra, y con una
  `badge` cuando no es un enemigo regular — "Hero of Oryx", "Hero
  Minion", "Encounter", "Beacon Guardian" — para no perder esa
  clasificación aunque ya no agrupe visualmente por ella). La segunda
  pestaña de nivel superior es el comparador de equipo y la tercera la
  Fame Checklist (ver más abajo las dos).
  Todo en JS vanilla, sin dependencias externas. Los iconos de
  poción/enemigo/mazmorra/bioma se sirven directo desde
  `realmeye.com/s/a/img/...` (hotlinking, sin copiarlos localmente);
  `data/equipment.json` en cambio se carga completo por `fetch()` en el
  cliente (880 KB) en vez de embeberse en el HTML, para no inflar la
  carga inicial de la pestaña de pociones.

- **`data/dungeon_potions.json`** — salida estructurada por mazmorra:
  `icon` (icono del portal), `difficulty` (float 0-10 en pasos de 0.5,
  sacado con regex de la caja "Difficulty: X" que trae cada página de
  mazmorra — se renderiza como calaveras reusando los mismos iconos que
  usa la propia wiki, `DIFFICULTY_FULL_ICON`/`DIFFICULTY_HALF_ICON` en
  `scraper.py`), `main.garantizados`, `main.extra`,
  `treasure.garantizados`, `treasure.extra` — cada entrada de esas
  listas es `{name, type, icon, guaranteed, label, source_name,
  source_href, source_icon}` — más `error` si la página no tiene
  sección "Drops of Interest" (mazmorras sin combate como Chess, Admin
  Arena, o páginas aún poco documentadas). `type` es la poción
  normalizada (`potion_type()` en `scraper.py`: quita "Greater"/"(SB)"
  y colapsa "Health Potion"→Life, "Magic Potion"→Mana, "Potion of
  X"→X) para que el filtro por tipo agrupe normal y greater juntos.
  `is_potion()` además descarta del todo Health Potion, Magic Potion,
  Loot Drop Potion, Loot Tier Potion y Potion of Max Level (no son de
  interés). Las mazmorras/enemigos que se quedan sin ninguna poción
  tras ese filtro no aparecen en el HTML (ver `build_html.py`,
  `render_card` devuelve `None` en ese caso).

- **`data/cache/`** — HTML crudo cacheado (~9 MB). Borrar para forzar
  refetch completo.

- **`data/biome_potions.json`** — enemigos de mundo abierto (no atados a
  una mazmorra), pero clasificados por **bioma** en vez de por el reparto
  arbitrario "Setpiece Bosses / Encounters" que traía `/wiki/quest-monsters`
  (sustituido por completo, ver
  [[0008-biome-classified-open-world-potions]]). `get_biome_list()`
  parsea `/wiki/the-realm`, secciones "Rookie/Adept/Veteran/Seasonal
  Biomes", y saca `{name, href, tier, icon}` para los 23 biomas
  implementados (el enlace al nombre va siempre envuelto en `<b><a
  href="...">`; biomas aún no implementados como Low Desert aparecen sin
  `<a>` y se descartan solos). `scrape_biome(name, href, tier)` visita la
  página propia de cada bioma, localiza el bloque entre el `<h2>`
  "Enemies" o "Monsters" y el siguiente `<h2>`, y lo trocea por sus
  subtítulos h3/h4 ("Regular Enemies", "Heroes of Oryx", "Heroes of Oryx
  Minions", "Encounters", "Beacon Guardian", a veces "NPCs" — el
  contenido que precede al primer subtítulo, en biomas cuya lista base
  no lleva subtítulo propio, se etiqueta "Regular Enemies"). Para cada
  enemigo de cada grupo, `get_enemy_potion_drops()` (la misma función
  que ya usaba el scraping de quest-monsters) mira directamente su
  propia tabla "Drops" — no hay tabla "Drops of Interest" del bioma que
  cruzar, cada enemigo es su propio "jefe", igual que un setpiece boss.
  Biomas/grupos sin ningún enemigo con pociones no aparecen en el JSON
  (los biomas Rookie casi siempre caen aquí — están pensados para subir
  de nivel, no para farmear pociones, según la propia wiki). Genera con
  `python3 scraper.py biomes data/biome_potions.json` (~23 biomas, unos
  300 enemigos individuales — la mayoría ya en caché tras el primer
  scrape de mazmorras si coinciden con bosses ya vistos).

## Cómo se decide "Guaranteed" vs "Possible"

(la clave interna del JSON sigue llamándose `garantizados`/`extra` por
estabilidad del esquema; en el HTML se muestran como "Guaranteed"/"Possible")

1. En la tabla "Drops of Interest" de la mazmorra, cada ítem lista qué
   enemigos lo sueltan.
2. Si alguno de esos enemigos aparece en la sección "Boss" (jefe
   principal) de la mazmorra → se consulta la tabla "Drops" de ESE
   enemigo concreto; si tiene el marcador G, va a "Guaranteed", si no,
   a "Possible".
3. Igual pero por separado para la sección "Treasure Room Boss" → bucket
   `treasure`.
4. Si el ítem solo lo sueltan enemigos normales/variables (no jefe), va
   directo a `main.extra` ("Possible") sin necesidad de consultar su
   página (nunca puede ser garantizado porque el enemigo no siempre
   aparece).

## Equipment Compare

- **`equipment_scraper.py`** — recorre 34 páginas de categoría de
  `/wiki/equipment` (12 líneas de arma, 19 de habilidad, 3 de armadura —
  **rings excluido**, ver [[0002-rings-excluded-from-equipment-scrape]]).
  Cada página tiene una o más tablas `<h4>Tiered/Untiered/Set Tiered/...
  </h4>` con una fila por ítem; `parse_item_tables()` es genérico: lee
  las cabeceras `<th>` reales de cada tabla y mapea celdas por posición,
  así que no hay que hardcodear columnas por tipo de arma/armadura. Cada
  ítem sale como `{name, href, icon, category, category_slug, family,
  tier, soulbound, stats: {ATT,DEF,...}, columns, effects: [...],
  effect_descriptions: {...}, classes: [...]}`. Las `classes` (quién
  puede equiparlo) se leen del primer párrafo de la página de categoría
  buscando enlaces a cualquiera de las 19 clases del juego (la frase
  varía: "used by X", "worn by X", "give X the ability to..." — de ahí
  que se busque por enlace de clase, no por frase fija) y se aplican a
  **todos** los ítems de esa página. Genera con `python3
  equipment_scraper.py data/equipment.json` (~1300 ítems, ~2.5 min: la
  mayoría son las 34 páginas de categoría, pero ~170 armas necesitan
  además una petición a su propia página — ver más abajo).
- **Páginas de categoría "delgadas"**: para las armas básicas Tiered
  (T0-T13) de casi todas las líneas de arma, la página de categoría no
  trae ni Shots, ni Rate of Fire, ni Effect(s) — solo el rango de daño,
  XP Bonus, Feed Power y Projectile. `enrich_thin_weapons()` detecta esos
  ítems (sin columna `Shots` ni `Fire Rate` ni grupos `Bullet N`), pide su
  página propia y reconstruye `columns['Damage (Average)']` +
  `effects`/`effect_descriptions` a partir de las tablas por proyectil de
  esa página — ver [[0005-thin-category-page-weapons]]. Comparte
  `fetch_projectile_groups()` con `enrich_multi_bullet_shots()`
  ([[0003-multi-bullet-dps]]).
- **Un mismo campo no debe vivir a veces como columna propia y a veces
  troceado dentro de `Damage (Average)`**: si un ítem tiene "Range" como
  columna de nivel superior y otro lo tiene como segmento embebido, el
  comparador pinta dos filas "Range" independientes en vez de una (una
  con el valor del primero y "—" al lado, otra al revés). Al final de
  `run_all()`, `normalize_collision_labels()` recorre TODO el dataset ya
  scrapeado, detecta cualquier label usado de las dos formas en algún
  sitio (no es una lista fija — encontró `Range` en Weapon y `Shots`/
  `Life Steal` en Ability, sin relación con `enrich_thin_weapons()`) y
  eleva cada aparición embebida a columna propia — ver
  [[0006-duplicate-range-rows]].
- **Ni tampoco debe vivir bajo dos nombres de columna distintos**: las
  páginas de categoría de Daggers y Dual Blades usan literalmente
  `Shots(Arc Gap)`/`Range(True Range)` como texto de cabecera donde el
  resto de categorías usan `Shots`/`Range` — incomparable con
  `normalize_collision_labels()` porque ahí ambos lados son columnas de
  nivel superior, solo que con nombres distintos. `HEADER_ALIASES` en
  `parse_item_tables()` normaliza esos nombres de cabecera concretos al
  leerlos (el matiz "arc gap"/"true range" no se pierde: ya va dentro del
  valor de la celda cuando aplica) — ver [[0007-header-name-aliases]].
- **`columns` está trocedado, no es texto plano**: cada celda de la wiki
  suele empaquetar varios datos en una sola casilla separados por
  `<br>` (ej. la columna "Damage (Average)" de un arma trae el rango de
  daño, la velocidad de proyectil, un efecto especial con su
  descripción, y el Rate of Fire, todo junto). `split_segments()`
  convierte eso en una lista `[{label, value}, ...]`: un `Bullet N:`
  detectado prefija las etiquetas de ese grupo, un patrón `Label: valor`
  se separa tal cual, un `[NombreEfecto] descripción` se separa en
  `{label: NombreEfecto, value: descripción}`, y el único trozo que
  queda sin etiquetar (normalmente el rango de daño en sí) usa la
  cabecera de columna como label. `effect_descriptions` sale de cruzar
  esos labels con la lista `effects` (nombres de efecto sacados de los
  `<img alt="...">` de la celda).
- **"Mismo tipo" para comparar** = mismo conjunto exacto de `classes`
  (no la categoría arma/habilidad/armadura). Es la regla que pidió Javi:
  dos ítems son comparables si los equipan exactamente las mismas
  clases, sin más restricciones — así Bows y Longbows (ambos
  Archer+Huntress+Bard) caen en el mismo grupo aunque sean líneas de
  arma distintas.
- La comparación en sí vive enteramente en el JS de `build_html.py`
  (`renderEqCompare` y alrededores): busca-y-selecciona Item A, filtra
  el picker de Item B al `classKey()` de A, y pinta filas de diff para
  stats numéricos (color verde/rojo según quién gana), Tier, XP
  Bonus/Feed Power y cualquier otra columna presente en A o B —
  `segmentRows()` expande cada columna trozeada en una fila por
  `{label, value}`, emparejando por label entre A y B (así "Damage
  (Average)", "Projectile Speed", el efecto embebido y "Rate of Fire"
  salen como cuatro filas independientes en vez de un bloque de texto) —
  más una sección de Effects con check/no-check por lado. Cuando la
  sección de DPS se muestra (ver más abajo), su propia fila "Rate of
  Fire" ya resume el RoF combinado de todos los bullets, así que
  `segmentRows()` recibe un `skipLabels` con las etiquetas `Rate of Fire`/
  `Bullet N Rate of Fire` presentes en A o B para no repetir la misma
  información dos veces — ver [[0007-header-name-aliases]].
- **DPS estimado** (solo si A y B son ambos `category === 'Weapon'` y se
  les puede parsear el daño): dos sliders ATT/DEX (0-100, default 75)
  alimentan `computeDps()`, que implementa las fórmulas exactas de
  `/wiki/character-stats` (verificadas contra los ejemplos numéricos que
  trae la propia página):
  `DamageMultiplier = 0.5 + ATT/50`,
  `baseAttacksPerSecond = 1.5 + 6.5*DEX/75`,
  y por cada "bullet group" del arma, `DPS += avgDamage * shots *
  DamageMultiplier * (baseAttacksPerSecond * RoF/100)`.
  ATT no afecta el daño de abilities según la wiki, así que el DPS no se
  calcula para esa categoría (ni para armor/rings, que no disparan).
- **Armas multi-bala** (ej. Heartsteel Claymore, Arcane Rapier — 2+
  segmentos `Bullet N` en `columns['Damage (Average)']`): `parseDamageProfile()`
  trata el Rate of Fire de cada bullet como la fracción de ataques (a la
  cadencia base compartida) que hace el daño de ESE bullet en vez del
  golpe normal, no como una cadencia de ataque independiente — ver
  [[0003-multi-bullet-dps]] (la propia página de Arcane Rapier lo confirma:
  "the Rapier's Lunge now triggers every 3 shots instead of 5" para su
  bullet 2 al 20% RoF). El bullet sin RoF explícito dispara al 100% de
  los ataques (es la convención de la wiki para "siempre dispara" — las
  flechas Main/Side de un Shortbow, por ejemplo, omiten ambas el RoF y
  las dos disparan siempre juntas; ver la nota al principio de
  [[0003-multi-bullet-dps]], corregida por
  [[0005-thin-category-page-weapons]]). El número de shots por bullet
  sale de un segmento `Bullet N Shots` que
  añade `enrich_multi_bullet_shots()` en `equipment_scraper.py` cuando la
  página de categoría no lo separa por bullet (fetch a la página propia
  del ítem, solo si el número de tablas "Shots" encontradas coincide
  exactamente con el número de bullets — si no, se deja 1 shot por bullet
  por defecto en vez de arriesgar un número incorrecto).
- **Armas con columna `Fire Rate` separada** (~30 ítems, sobre todo
  Longbows, ej. Anteros Longbow, Morning Star of Harrowing Memories): en
  vez de un `Rate of Fire` embebido en la celda de daño, estas listan una
  columna `Fire Rate` aparte con un % por disparo (ej. `"15%, 50%, 90%,
  50%, 15%"` para 5 disparos que comparten el mismo daño medio) o, si
  cada grupo tiene su propia etiqueta compartida entre columnas (ej.
  `Main`/`Side` en Hama Yumi), un % por etiqueta. `parseDamageProfile()`
  detecta ambas formas antes de caer al camino de un solo grupo — ver
  [[0004-fire-rate-column-dps]]. Un ítem (Morning Square) no encaja en
  ninguna de las dos formas (su columna "Fire Rate" son en realidad 3
  definiciones de proyectil independientes, cada una potencialmente
  multi-disparo) y se queda como hueco conocido: su DPS calculado
  infravalora el real en vez de arriesgar un número inventado.

## Fame Checklist

Tercera pestaña de nivel superior. Es la tabla **"Dungeon Collection"**
de `/wiki/fame-bonuses` convertida en checklist: cada una de sus 13 filas
(Tunnel Rat, Explosive Journey, ... Realm of the Mad God) es una sección
con su bonus, y cada mazmorra de esa fila un checkbox. La otra tabla de
"Dungeon Bonuses" (Dungeon Completion) **no** entra: es repetible y su
unidad es un contador de completadas, no un booleano — ver
[[0009-fame-collection-dungeon-aliases]].

- **`data/fame_bonuses.json`** — una entrada por colección: `name`,
  `requirement` ("Complete each 1 time"), `subtitle` ("Wild Shadow era
  dungeons"), `bonus` (texto tal cual, `+7.5%, +3,000 Fame`), `fame` y
  `percent` ya parseados, y `dungeons` = `[{name, href, icon,
  difficulty}]`. La celda
  "Threshold" de la wiki empaqueta requisito, etiqueta del conjunto y
  lista de mazmorras separados por `<br>` dentro de una sola casilla, así
  que `scrape_fame_collections()` la trocea por `<br>`: los dos primeros
  trozos son requisito y subtítulo, el resto son nombres de mazmorra. Los
  nombres van en texto plano (sin enlace), así que el `href`/`icon` de
  cada una se cruza contra `get_dungeon_list()`; lo que no aparezca ahí
  sale con `href`/`icon` a `null` y se pinta con el icono de relleno (hoy
  no hay ninguna: las 84 mazmorras tienen icono).
  `DUNGEON_NAME_ALIASES` normaliza `Ice Cave` → `Ice Citadel`, el único
  nombre de la tabla que ya no existe en la wiki. `difficulty` sale de la
  página de cada mazmorra con el mismo `get_difficulty()` que usa el
  scraper de pociones (viene de la caché, así que es gratis); las tres
  de temporada (Santa's Workshop, Rainbow Road, Beachzone) no tienen caja
  "Difficulty" y quedan a `null`.
- **Orden**: el JSON conserva el orden de la wiki; ordena `build_html.py`
  al pintar. Dentro de cada colección las mazmorras van de fácil a
  difícil (`difficulty_key`; las sin valorar cuentan como 0, así que
  abren la colección) y cada fila lleva sus calaveras. Las colecciones se
  ordenan por la mazmorra más difícil que contienen y, a igual máximo,
  por la media (`collection_key`, también con las sin valorar a 0): First
  Steps abre y Conqueror of the Realm cierra. La suite comprueba las dos
  cosas.
- **Estado en el cliente**: los ticks viven en `localStorage` bajo
  `rotmg-toolkit:fame-dungeons` (array de nombres de mazmorra), envuelto
  en `try/catch` para que la página siga funcionando en modo privado. La
  clave de cada checkbox es el atributo `data-dungeon`, no el `href`: al
  marcar uno, el JS marca **todos** los checkboxes con ese mismo
  `data-dungeon`, así que una mazmorra que sale en varias colecciones
  (Pirate Cave está en cuatro) se marca en todas a la vez — que es como
  lo cuenta el juego.
- **Buscador rápido** (`.fame-picker`, arriba del todo): al enfocarlo
  despliega las 65 mazmorras distintas en orden alfabético, cada una con
  su checkbox, su icono y en cuántas colecciones sale; escribir filtra la
  lista y se puede marcar/desmarcar ahí mismo sin bajar a las secciones.
  El catálogo **se deriva del propio DOM** (`fameCatalog` recorre los
  `.fame-item` ya pintados), no de un segundo bloque de datos: así no hay
  dos copias de la lista que puedan desincronizarse. `fameNorm()`
  normaliza el apóstrofo tipográfico de la wiki (`Oryx’s`) al recto que
  produce un teclado, para que escribir `oryx's` encuentre las tres. El
  desplegable se cierra con Escape (la primera pulsación limpia el texto)
  o con un clic fuera, pero **no** al marcar: se pueden tildar varias
  seguidas. Las filas que no casan se ocultan con el atributo `hidden`,
  que **solo funciona** porque la hoja lleva una regla de autor
  `[hidden] { display:none !important; }`: sin ella, el `display:flex` de
  `.fame-result` gana al del user-agent y el filtro no filtra nada — ver
  [[0010-hidden-attribute-loses-to-author-display]].
- **Lo que se recalcula en cada cambio** (`fameRender()`): el contador y
  la barra de progreso de cada sección, la clase `.done` de las secciones
  completas, las filas del buscador, y el resumen de arriba (mazmorras
  marcadas, colecciones completas y fama acumulada de esas colecciones,
  sobre un total de 65 mazmorras distintas y 46.100 de fama). El botón
  **Clear all** vacía el conjunto entero, previa confirmación.

## Tests

`npm test` (`tests/fame.spec.mjs`) abre `index.html` en un **Chromium
real** vía `playwright-core` y comprueba la Fame Checklist entera: el
desplegable, el filtrado, marcar desde los dos sitios, la sincronización
entre secciones, el progreso, la persistencia tras recargar, el botón
Clear all y un viewport de 400px. Las asserts miran `:visible`, no el
atributo o la clase que debería ocultar algo: es la única forma de
detectar bugs de cascada CSS, y jsdom da respuestas falsas sobre eso
([[0010-hidden-attribute-loses-to-author-display]] explica el caso y cómo
arrancar Chromium en este NUC sin sudo).

## API estática

`build_api.py` lee `data/*.json` (la salida de los tres scrapers de
arriba) y escribe `api/`: un array grande por recurso
(`api/dungeons.json`, `api/biomes.json`, `api/equipment.json`,
`api/potion-types.json`) más un fichero pequeño por ítem
(`api/dungeons/{slug}.json`, etc.) y un manifiesto `api/index.json`. Es
la única capa donde se traducen los nombres de campo internos
(`garantizados`/`extra`, `href`...) a un contrato público en inglés
(`guaranteed`/`possible`, `wikiUrl`, `slug`...) — `data/*.json` sigue
siendo el formato interno que usan `build_html.py` y `build_api.py`, no
hay que tocarlo para cambiar el contrato de la API.

Documentación completa del esquema (con ejemplos) en
[`api/README.md`](../api/README.md). Puramente estático: son ficheros
JSON de verdad en disco, no hay servidor detrás — cualquier hosting de
estáticos (GitHub Pages incluido) los sirve tal cual.

## Servir la página en la red local

```
python3 -m http.server 8090 --bind 0.0.0.0 --directory /home/javi/rotmg-info
```

Accesible como `http://192.168.1.3:8090/index.html` desde cualquier
dispositivo de la LAN.

## Regenerar datos

Todo junto:

```
cd /home/javi/rotmg-info
./refresh.sh
```

O paso a paso:

```
cd /home/javi/rotmg-info
python3 scraper.py all data/dungeon_potions.json                 # ~5 min, red
python3 scraper.py biomes data/biome_potions.json                # ~3-4 min, red
python3 scraper.py fame data/fame_bonuses.json                   # ~segundos, red
python3 equipment_scraper.py data/equipment.json                 # ~1 min, red
python3 build_html.py data/dungeon_potions.json index.html data/biome_potions.json data/equipment.json data/fame_bonuses.json
python3 build_api.py api
```
