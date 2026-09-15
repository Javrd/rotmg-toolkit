---
id: TASK-001
title: 'Fame checklist: Dungeon Collection con estado por mazmorra'
status: Done
assignee: []
created_date: '2026-09-15 21:37'
updated_date: '2026-09-15 21:44'
labels: []
dependencies: []
priority: high
ordinal: 100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Nueva pestaña de nivel superior en index.html con la tabla 'Dungeon Collection' de /wiki/fame-bonuses convertida en checklist: una sección por bonus (Tunnel Rat, Explosive Journey, ...) y un check por mazmorra. El estado se guarda en localStorage y una misma mazmorra marcada en una sección se marca en todas.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 scraper.py extrae la tabla Dungeon Collection a data/fame_bonuses.json
- [ ] #2 Una sección por fila de la tabla, con su bonus visible
- [ ] #3 No se muestra la columna Repeatable (siempre False en esa tabla)
- [ ] #4 Marcar una mazmorra la marca en todas las secciones donde aparece
- [ ] #5 Botón 'Clear all' que desmarca todo
- [ ] #6 El estado sobrevive a recargar la página
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
scraper.py: scrape_fame_collections()/run_fame() parsean la tabla Dungeon Collection de /wiki/fame-bonuses a data/fame_bonuses.json. build_html.py: tercera pestaña de nivel superior con una sección por colección, checkbox por mazmorra, barra de progreso por sección y resumen global. Estado en localStorage (rotmg-toolkit:fame-dungeons), sincronizado por data-dungeon entre secciones. Verificado con jsdom (22 checks: sync entre las 4 secciones de Pirate Cave, progreso, colección completa, persistencia tras recarga, clear all, alias Ice Cave).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fame Checklist en producción: 13 colecciones, 65 mazmorras distintas, 46.100 de fama en juego. Ice Cave se normaliza a Ice Citadel (ADR 0009). Dungeon Completion queda fuera (TASK-003).
<!-- SECTION:FINAL_SUMMARY:END -->
