---
id: TASK-006
title: Iconos de mazmorra ausentes (Oryx's Castle)
status: Done
assignee: []
created_date: '2026-09-15 22:42'
labels: []
dependencies: []
priority: medium
ordinal: 130
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/wiki/dungeons no trae thumbnail para Oryx's Castle (se entra desde el reino, no por portal), así que salía con el placeholder gris en la checklist y en la pestaña de pociones. Su propia página sí muestra el portal como <img title='X Portal'>.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Ninguna mazmorra usa el icono de relleno
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
get_portal_icon(href) en scraper.py, usado solo como fallback desde get_dungeon_list() cuando la lista no trae icono. Validado contra las 84 mazmorras: 71 coinciden exactamente con el icono de la lista, 1 recuperada (Oryx's Castle); las 11 que difieren son variantes .gif/.png o arte distinto, por eso el icono de la lista sigue teniendo prioridad y el diff se limita a Oryx's Castle. Verificado en Chromium: 271 iconos de la Fame Checklist, 0 fallan al cargar.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Oryx's Castle ya sale con su portal; 84/84 mazmorras con icono.
<!-- SECTION:FINAL_SUMMARY:END -->
