---
id: TASK-009
title: 'Fame Checklist: skin y tintes por personaje'
status: Done
assignee: []
created_date: '2026-10-06 16:29'
updated_date: '2026-10-06 16:36'
labels: []
dependencies: []
priority: medium
ordinal: 165
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Cada personaje puede llevar skin, tinte de ropa y tinte de accesorio, pintados como en el juego para reconocerlos y distinguir repetidos de una clase. Los datos (skins por clase, tintes, hoja de sprites con máscaras de tinte) salen de los JS de RealmEye en tiempo de scrape; el render es el mismo compositing de canvas que usa RealmEye. Se guardan los mismos IDs que RealmEye (skin id, código de tinte) para que TASK-008 pueda importar el aspecto.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Al crear o editar un personaje se elige skin (de las de su clase), tinte de ropa y tinte de accesorio, con vista previa
- [x] #2 La baldosa del personaje muestra su sprite con skin y tintes
- [x] #3 Los ids guardados son los de RealmEye (data-skin, data-dye1/2)
- [x] #4 npm test cubre crear con aspecto, editarlo, persistencia y que el render no queda en blanco
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
outfit_scraper.py copia de los JS de RealmEye (classinfo/sheet/definition) data/outfits.json (19 clases, 1466 skins, 389 tintes) y data/outfits.png (hoja de sprites, 891 KB). El diálogo de alta pasa a dos pasos (clase → aspecto con pestañas Skin/Clothing/Accessory y buscador); ✎ en cada baldosa reabre el aspecto. Render en canvas = compositing de RealmEye. Los tests ahora sirven el repo por HTTP. ADR 0012.
<!-- SECTION:FINAL_SUMMARY:END -->
