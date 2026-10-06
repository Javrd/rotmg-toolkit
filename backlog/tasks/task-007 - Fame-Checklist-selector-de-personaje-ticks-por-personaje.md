---
id: TASK-007
title: 'Fame Checklist: selector de personaje (ticks por personaje)'
status: Done
assignee: []
created_date: '2026-10-06 15:42'
updated_date: '2026-10-06 16:10'
labels: []
dependencies: []
priority: high
ordinal: 160
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Los bonus de Dungeon Collection son por personaje, así que la checklist necesita un estado por personaje. Panel de personajes junto a la Fame Checklist (solo en esa pestaña): una baldosa por personaje y un + al final que abre un selector de clase. Una columna, dos cuando se llena, y luego scroll propio. Borrar con confirmación. Sin personajes la checklist funciona igual y el primero que se cree hereda esos ticks. Varios de la misma clase se numeran (Wizard, Wizard 2).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Varios personajes de la misma clase conviven sin problema
- [x] #2 Los ticks guardados hoy se migran a un personaje inicial sin perder nada
- [x] #3 npm test cubre cambiar de personaje, persistencia por personaje y la migración
- [x] #4 Panel con + y selector de clase para crear, cambiar y borrar (con confirmación) personajes; cada uno con sus propios ticks; una columna, dos al llenarse, luego scroll
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 Los scrapers afectados corren sin error y `data/*.json` queda regenerado y commiteado.
- [x] #2 `python3 build_html.py ...` regenera `index.html` sin error y la pestaña tocada se ha abierto en un navegador/servidor local.
- [x] #3 `python3 build_api.py api` regenerado si el cambio toca el contrato público.
- [x] #4 `docs/ARCHITECTURE.md` describe el sistema tal y como queda (sin historia).
- [x] #5 Si hubo una decisión no obvia o un bug con causa raíz, hay una ADR nueva en `docs/decisions/`.
- [x] #6 Commit en `main` y push a `origin` (GitHub Pages despliega desde ahí).
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Panel .char-panel con selector de clase (<dialog>, 19 clases scrapeadas de /wiki/classes a data/classes.json), estado por personaje en localStorage rotmg-toolkit:fame-characters, herencia de los ticks sueltos por el primer personaje, una→dos columnas→scroll vía charsFit(), tira horizontal en ≤800px. Sin renombrar: el nombre es clase + número fijo (ADR 0011). npm test: 114 checks en Chromium.
<!-- SECTION:FINAL_SUMMARY:END -->
