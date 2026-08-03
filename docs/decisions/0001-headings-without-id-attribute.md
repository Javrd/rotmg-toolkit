# 0001 — Los `<h2>`/`<h3>` de RealmEye no siempre tienen `id`

## Contexto

El parser de `scraper.py` divide cada página de mazmorra en secciones
buscando `<h2 id="...">Título</h2>` / `<h3 id="...">Título</h3>` para
saber qué bloque de HTML corresponde a "Boss", "Treasure Room Boss",
"Drops of Interest", etc.

En algunas páginas (ej. `toxic-sewers`) los sub-encabezados dentro de una
sección no llevan `id`, por ejemplo:

```html
<h2 id="boss">Boss</h2>
...Gulpord the Slime God...
<h2>Treasure Room Boss</h2>
...Master Rat...
<h2>Special Encounter</h2>
...Golden Rat...
```

La primera versión del regex (`<h([23]) id="([^"]*)">...`) exigía el
atributo `id`, así que "Treasure Room Boss" y "Special Encounter" no se
reconocían como límites de sección: su contenido quedaba fusionado
dentro de la sección "Boss" anterior. Resultado: Master Rat y Golden Rat
se clasificaban como parte del jefe principal, y una poción sin
garantizar (soltada solo por Master Rat en la sala del tesoro) aparecía
como "Garantizados" de la mazmorra entera — dato incorrecto.

## Decisión

El regex de encabezados hace el `id` opcional:
`<h([23])(?:\s+id="([^"]*)")?>([^<]*)</h\1>`. Los encabezados se
identifican por su **texto** ("Boss", "Treasure Room Boss", "Drops of
Interest", comparado en minúsculas), nunca por el `id`, precisamente
porque el `id` no está garantizado.

## Consecuencias

- Cualquier heurística futura sobre estructura de esta wiki debe asumir
  que el `id` es opcional y que solo el texto visible del encabezado es
  fiable.
- Antes de confiar en un dato de "guaranteed"/boss para una mazmorra
  nueva, conviene volcar `split_sections()` y revisar visualmente qué
  quedó agrupado dentro de "Boss", por si vuelve a pasar con otro
  patrón no previsto.
