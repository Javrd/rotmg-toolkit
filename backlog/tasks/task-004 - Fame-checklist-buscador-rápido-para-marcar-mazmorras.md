---
id: TASK-004
title: 'Fame checklist: buscador rápido para marcar mazmorras'
status: Done
assignee: []
created_date: '2026-09-15 22:01'
updated_date: '2026-09-15 22:02'
labels: []
dependencies: []
priority: high
ordinal: 150
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Un buscador arriba de la Fame Checklist que al enfocarlo despliega TODAS las mazmorras en orden alfabético, se filtra escribiendo, y permite marcar/desmarcar directamente desde el desplegable sin bajar a las secciones. Comparte estado con los checkboxes de las secciones.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Al enfocar el input se despliegan las 65 mazmorras distintas en orden alfabetico
- [ ] #2 Escribir filtra la lista
- [ ] #3 Marcar desde el desplegable actualiza las secciones, el progreso y localStorage
- [ ] #4 El desplegable se cierra con Escape o clic fuera, y sigue abierto tras marcar
- [ ] #5 La lista sale del propio DOM: no duplica los datos scrapeados
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
Buscador .fame-picker arriba de la Fame Checklist. El catálogo se deriva del DOM (fameCatalog recorre los .fame-item), así que no duplica los datos scrapeados. fameNorm() normaliza el apóstrofo tipográfico para que 'oryx's' encuentre Oryx's Castle/Chamber/Sanctuary. Cierra con Escape (1ª pulsación limpia el texto) o clic fuera, nunca al marcar. Verificado con jsdom: 46 checks en total, 24 nuevos (orden alfabético, filtro, apóstrofo, estado vacío, tick bidireccional picker<->secciones, apertura/cierre, clear all).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
65 mazmorras A-Z en el desplegable, marcables sin bajar a las secciones.
<!-- SECTION:FINAL_SUMMARY:END -->
