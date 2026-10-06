# 0011 — Personajes locales: RealmEye no se puede leer desde el navegador

## Contexto

Los bonus de Dungeon Collection son por personaje, así que la Fame
Checklist necesitaba un estado por personaje. La idea de partida era
sacar los personajes de RealmEye: recordar el usuario, leer
`/player/<usuario>` (vivos) y `/graveyard-of-player/<usuario>`
(muertos), dar de alta los nuevos y quitar los que mueren.

Comprobado el 2026-10-06:

- **RealmEye no manda `Access-Control-Allow-Origin`.** Un `fetch()` desde
  `javrd.github.io` sale y recibe respuesta, pero el navegador no deja que
  el JS la lea. Da igual omitir las cookies (`credentials: "omit"`): el
  navegador no sabe si una respuesta es pública (una intranet o el router
  también responden sin cookies), así que solo deja leerla si el servidor
  lo autoriza. Tampoco sirven `mode: "no-cors"` (respuesta opaca) ni un
  iframe (`x-frame-options: sameorigin`). Los `<img>` de RealmEye sí
  funcionan porque se muestran, no se leen.
- **Las filas de personaje no traen ningún ID**, ni en la lista de vivos
  ni en el cementerio: emparejar "este muerto es mi Wizard 2" solo se
  puede deducir por clase, fama y fecha. En el perfil de Javi además
  "Last seen" está oculto.
- No se pudo comprobar si `/player/` lista varios personajes de la misma
  clase: ningún perfil visible tenía repetidos.
- Con el user-agent `Mozilla/5.0` a secas RealmEye responde `204` vacío;
  con un UA de navegador completo (el de `scraper.py`), `200`.

## Decisión

Los personajes se crean a mano y viven solo en `localStorage`. Un
personaje es la clase más un número fijo que distingue a los repetidos
("Wizard", "Wizard 2"). Ese número no cambia aunque se borren otros, para
que no cambie el nombre de un personaje. La checklist sigue funcionando
sin ningún personaje, y el primero que se crea hereda esos ticks: así no
se pierde lo marcado antes de que existieran los personajes.

La sincronización con RealmEye queda en TASK-008, pendiente de elegir un
intermediario fuera del navegador: el NUC publicando un JSON por usuario
en una rama que se lea vía `raw.githubusercontent.com` (que sí manda
CORS), o un Worker de Cloudflare. Un proxy CORS público se descarta por
frágil y porque un tercero vería las peticiones.

## Consecuencias

- Los personajes no se comparten entre navegadores ni dispositivos.
- Un personaje muerto hay que borrarlo a mano hasta que exista TASK-008.
- Si llega la sincronización, el emparejamiento con RealmEye será por
  clase + fama y tendrá que pedir confirmación cuando haya repetidos de
  una clase. El modelo `{id, cls, n, done}` no depende de RealmEye: la
  sincronización solo añadiría y quitaría entradas.
