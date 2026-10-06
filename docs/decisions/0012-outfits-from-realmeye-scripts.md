# 0012 — Skins y tintes: los datos y el render de RealmEye, copiados al repo

## Contexto

Javi quería ponerle a cada personaje su skin y sus tintes para
distinguirlos y reconocer los que tiene en el juego. La wiki solo trae
imágenes sueltas de cada skin (`/wiki/wizard-skins`) y el icono de botella
de cada tinte (`/wiki/dyes`). Con eso no se puede pintar un personaje
teñido: el tinte se aplica sobre zonas concretas del sprite, y esas zonas
no salen en ninguna imagen de la wiki.

RealmEye sí pinta personajes teñidos en sus páginas de jugador, en el
navegador, a partir de tres scripts estáticos:

- `classinfo.js` — skins por clase: `[skinId, nombre, índiceEnLaHoja]`.
- `sheet.js` — `sheetSrc`, un PNG en data-URL de 32750×960 con todas las
  skins (cada una con su sprite, y máscara y capa para ropa y para
  accesorio) y las texturas de las telas; y `sheetOffsets`, que asocia
  cada código de tinte a sus ítems y, si es tela, a su textura en la hoja.
- `definition.js` — nombres de ítem (de ahí salen los nombres de tinte).

Un prototipo con el mismo algoritmo pintó correctamente los cinco
personajes de Javi a partir de los `data-*` de su perfil, incluidos los
tintes de tela.

## Decisión

`outfit_scraper.py` descarga los tres scripts en tiempo de scrape y deja
en el repo `data/outfits.json` (clases, skins y tintes) y
`data/outfits.png` (la hoja decodificada). La página los carga la primera
vez que se abre la Fame Checklist y repite en canvas el compositing de
RealmEye.

Se descartó cargar `sheet.js` y `classinfo.js` de RealmEye directamente
con `<script src>`. Funcionaría, porque cargar un script de otro dominio
no necesita CORS (ver [[0011-characters-local-realmeye-not-readable-from-browser]]),
pero ejecutaría código ajeno en nuestro origen. Además las rutas llevan un
segmento de versión (`/s/hu/js/`) que, al cambiar, rompería la página
hasta el siguiente scrape. Copiar los datos los fija y los deja
revisables en git.

Se guardan los ids de RealmEye tal cual (`skin` = `data-skin`, `dye1`/`dye2`
= `data-dye1`/`data-dye2`), no índices propios: así una sincronización con
RealmEye (TASK-008) puede copiar el aspecto de un personaje sin traducir
nada, y usarlo para emparejar personajes repetidos de una clase.

## Consecuencias

- El repo lleva una imagen de ~900 KB, y cada vez que RealmEye añada
  skins y se re-scrapee entrará una versión nueva. Si no cambia, el
  fichero es idéntico y no hay diff.
- La hoja y los datos son de RealmEye (que a su vez saca los sprites del
  juego). El sitio ya enlazaba todos sus iconos directamente a RealmEye;
  esto va un paso más allá, porque copia un recurso suyo.
- Si RealmEye cambia el formato de esos scripts, el scraper falla en vez
  de producir datos a medias: busca los tres scripts en `/recent-deaths`
  y lanza error si falta alguno, y los regex de `sheetSrc` y
  `sheetOffsets` fallan si no encuentran nada.
- Sin la hoja (offline, fallo de carga), la baldosa muestra el retrato
  de la clase y el editor avisa. La checklist no depende del aspecto.
