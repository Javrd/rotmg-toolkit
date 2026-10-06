---
id: TASK-008
title: 'Fame Checklist: sincronizar personajes con RealmEye'
status: To Do
assignee: []
created_date: '2026-10-06 15:42'
updated_date: '2026-10-06 16:10'
labels: []
dependencies:
  - TASK-007
priority: medium
ordinal: 170
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Recordar el nombre de usuario de RealmEye y, a partir de /player/<user> (vivos) y /graveyard-of-player/<user> (muertos), proponer altas de personajes nuevos y quitar los que aparezcan en el cementerio. RealmEye no da ID de personaje: el emparejamiento es por clase + fama/fecha, con confirmación cuando hay varios de la misma clase. Bloqueo: RealmEye no manda CORS, así que hace falta un intermediario fuera del navegador (NUC → JSON en rama leída vía raw.githubusercontent.com, o Worker de Cloudflare); contexto y opciones en docs/decisions/0011. Pendiente de que Javi elija transporte.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 El usuario de RealmEye se guarda en el navegador y se puede cambiar
- [ ] #2 Personajes vivos de RealmEye que no están en la lista se ofrecen para añadir
- [ ] #3 Un personaje que aparece en el cementerio se marca como muerto y se puede quitar (o se quita solo)
- [ ] #4 Personajes ocultos en RealmEye o usuario inexistente dan un mensaje claro, no un fallo silencioso
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Los scrapers afectados corren sin error y `data/*.json` queda regenerado y commiteado.
- [ ] #2 `python3 build_html.py ...` regenera `index.html` sin error y la pestaña tocada se ha abierto en un navegador/servidor local.
- [ ] #3 `python3 build_api.py api` regenerado si el cambio toca el contrato público.
- [ ] #4 `docs/ARCHITECTURE.md` describe el sistema tal y como queda (sin historia).
- [ ] #5 Si hubo una decisión no obvia o un bug con causa raíz, hay una ADR nueva en `docs/decisions/`.
- [ ] #6 Commit en `main` y push a `origin` (GitHub Pages despliega desde ahí).
<!-- DOD:END -->
