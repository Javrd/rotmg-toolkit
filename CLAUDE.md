# rotmg-info

Scraper y fichas de equipo de RotMG. Publicado en el remoto
`rotmg-toolkit` (GitHub Pages sirve `main`: un push a `main` **es** el
despliegue).

## Documentación

Cuatro sitios, y ninguno se mezcla con otro:

- `backlog/tasks/` — **lo pendiente**. Se muta con la CLI, nunca a mano.
- `docs/decisions/NNNN-*.md` — **por qué** se decidió algo, un fichero por
  decisión, inmutable salvo para marcar `Superseded by`. No es lectura
  obligatoria de entrada.
- `docs/design/*.md` — cómo funciona **hoy**. Se edita en el sitio; nunca
  acumula bloques de "actualización del día X".
- `docs/ARCHITECTURE.md` — el sistema ahora, sin historia.

Para ponerse al día: `docs/ARCHITECTURE.md` + `npx backlog task list --plain`.

La CLI crea `backlog/decisions/`, `backlog/docs/` y `backlog/milestones/`:
**no se usan**. Nunca `backlog decision create`. El pendiente no vive en
ningún otro sitio — ni en GitHub Issues (`atalaya` `decisions/0010`).

## Cómo se trabaja aquí

- La cola la manda el `ordinal`, no la etiqueta de prioridad:
  `npx backlog task list --status "To Do" --sort ordinal --plain`.
- Todo es stdlib de Python 3 — no hay pip ni venv en este NUC. Nada de
  `requests`/`bs4`.
- `./refresh.sh` re-scrapea todo y regenera `index.html` + `api/`. Los
  scrapers cachean HTML crudo en `data/cache/` (no versionado), así que
  re-ejecutar es barato.
- `npm test` corre la suite de UI en un Chromium real
  (`tests/fame.spec.mjs`). Si tocas la Fame Checklist, pásala: jsdom
  miente sobre la cascada CSS y por eso ya se coló un filtro roto
  (`docs/decisions/0010`).
- `node_modules/` solo existe para `backlog.md` y `playwright-core`; el
  sitio no tiene dependencias de runtime.
