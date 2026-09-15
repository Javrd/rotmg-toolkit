---
id: TASK-003
title: 'Dungeon Completion: contadores de fama por mazmorra'
status: To Do
assignee: []
created_date: '2026-09-15 21:37'
labels: []
dependencies: []
priority: low
ordinal: 300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
La segunda tabla de Dungeon Bonuses (Dungeon Completion) es repetible y tiene cinco umbrales (1/10/20/40/100) con fama creciente. No entra en la checklist de colecciones; si se quiere, es una vista propia con contador por mazmorra, no un checkbox.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 Los scrapers afectados corren sin error y `data/*.json` queda regenerado y commiteado.
- [ ] #2 `python3 build_html.py ...` regenera `index.html` sin error y la pestaña tocada se ha abierto en un navegador/servidor local.
- [ ] #3 `python3 build_api.py api` regenerado si el cambio toca el contrato público.
- [ ] #4 `docs/ARCHITECTURE.md` describe el sistema tal y como queda (sin historia).
- [ ] #5 Si hubo una decisión no obvia o un bug con causa raíz, hay una ADR nueva en `docs/decisions/`.
- [ ] #6 Commit en `main` y push a `origin` (GitHub Pages despliega desde ahí).
<!-- DOD:END -->
