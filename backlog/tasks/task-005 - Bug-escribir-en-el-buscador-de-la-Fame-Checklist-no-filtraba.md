---
id: TASK-005
title: 'Bug: escribir en el buscador de la Fame Checklist no filtraba'
status: Done
assignee: []
created_date: '2026-09-15 22:15'
labels: []
dependencies: []
priority: high
ordinal: 120
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
El atributo hidden no ocultaba las filas porque .fame-result declara display:flex, que gana al [hidden] del user-agent. La suite jsdom no lo detectaba (getComputedStyle devolvía 'none' en jsdom y 'flex' en Chromium).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Escribir reduce la lista a lo que coincide, verificado en un navegador real
- [ ] #2 La suite de UI corre en Chromium y falla con el build roto
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
Regla [hidden]{display:none!important} en la hoja de build_html.py. Suite portada a Playwright (tests/fame.spec.mjs, npm test): 38 checks, incluidos viewport de 400px. Causa raíz y receta para correr Chromium sin sudo en docs/decisions/0010.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Filtrado arreglado y verificado en Chromium: 'snake' pasa de 65 filas visibles a 1.
<!-- SECTION:FINAL_SUMMARY:END -->
