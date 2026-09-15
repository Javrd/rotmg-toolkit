---
id: TASK-002
title: Exponer las colecciones de fama en la API estática
status: To Do
assignee: []
created_date: '2026-09-15 21:37'
labels: []
dependencies: []
priority: medium
ordinal: 200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
build_api.py no publica data/fame_bonuses.json. Añadir api/fame-collections.json (+ fichero por colección y entrada en api/index.json) traduciendo los nombres internos al contrato público en inglés, como el resto de recursos.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 api/fame-collections.json y api/fame-collections/{slug}.json generados
- [ ] #2 api/index.json y api/README.md documentan el recurso nuevo
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
