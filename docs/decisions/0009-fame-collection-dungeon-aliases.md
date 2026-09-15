# 0009 — Checklist de fama: solo "Dungeon Collection", y alias Ice Cave → Ice Citadel

## Contexto

`/wiki/fame-bonuses` tiene una sección "Dungeon Bonuses" con **dos**
tablas distintas:

1. **Dungeon Collection** — 13 filas (Tunnel Rat, Explosive Journey,
   Travel of the Decade, ... Realm of the Mad God). Cada fila es un
   conjunto de mazmorras que hay que completar **una vez cada una** para
   cobrar un bonus (`+7.5%, +3,000 Fame`). La columna `Repeatable` vale
   `False` en las 13 filas.
2. **Dungeon Completion** — una fila por mazmorra, con cinco umbrales
   (1/10/20/40/100 completadas) y fama creciente. `Repeatable` vale
   `True` en todas.

Javi pidió "una checklist con una sección por tabla (Tunnel Rat,
Explosive Journey, etc.)" y que no se mostrase `Repeatable` porque
"siempre es False". Ese "siempre False" solo es cierto en la primera
tabla, así que la petición identifica sin ambigüedad la tabla Dungeon
Collection: sus **filas** son las secciones de la checklist y sus
mazmorras, los checkboxes.

La segunda tabla no es marcable con un booleano — su unidad es un
contador de completadas por mazmorra, no un "hecho / no hecho".

Además, los nombres de mazmorra de la tabla van en texto plano (sin
enlace) y uno de ellos no existe: la fila "Realm of the Mad God" lista
**Ice Cave**, mientras que "Explosive Journey", "Conqueror of the Realm"
y "Hero of the Nexus" listan **Ice Citadel**. `/wiki/dungeons` solo
conoce Ice Citadel y `/wiki/ice-cave` responde `204 No Content` (página
inexistente): Ice Cave es el nombre previo al renombrado in-game. Sin
tratarlos como el mismo sitio, marcar Ice Citadel dejaría "Realm of the
Mad God" en 48/49 para siempre.

## Decisión

- La checklist cubre **solo** la tabla Dungeon Collection. La columna
  `Repeatable` no se scrapea ni se muestra. Dungeon Completion queda
  fuera y con tarea propia en el backlog (TASK-003): si algún día entra,
  es una vista con contador por mazmorra, no checkboxes.
- `DUNGEON_NAME_ALIASES` en `scraper.py` normaliza `Ice Cave` →
  `Ice Citadel` al parsear. Es un dict explícito, no un fuzzy match: si
  la wiki vuelve a desalinear un nombre, `run_fame()` lo canta por
  stderr ("Not found in /wiki/dungeons") en vez de inventarse una
  equivalencia.
- La clave de sincronización entre secciones es el **nombre ya
  normalizado** de la mazmorra (`data-dungeon` en el HTML), no el
  `href`: hay entradas sin página propia en `/wiki/dungeons`
  (Oryx's Castle no trae icono ahí) y el nombre es lo único presente en
  las 13 filas.
- El estado vive en `localStorage` (`rotmg-toolkit:fame-dungeons`, un
  array de nombres), no en el JSON scrapeado: es progreso personal de
  quien abre la página, y el sitio es estático sin backend.

## Consecuencias

- Marcar una mazmorra la marca en todas las colecciones donde aparece,
  que es justo lo que pidió Javi y además lo correcto respecto al juego:
  el juego cuenta una completada, no una por colección.
- 65 mazmorras distintas en 13 colecciones; el total de fama en juego por
  colecciones es 46.100.
- Si RealmEye añade una colección o cambia un nombre, basta con
  `python3 scraper.py fame data/fame_bonuses.json` + rebuild. Un nombre
  nuevo que no exista en `/wiki/dungeons` sale sin icono pero se muestra
  igual: la checklist no se rompe, solo pierde el icono.
- Riesgo asumido: si la wiki renombra una mazmorra ya marcada, el tick
  guardado en `localStorage` se queda huérfano (el nombre viejo ya no
  aparece en ninguna sección) y esa mazmorra sale desmarcada. Se arregla
  añadiendo el alias correspondiente.
