# rotmg-info

Scraper y fichas de equipo de RotMG. Publicado en el remoto `rotmg-toolkit`.

## Lo pendiente va a Backlog.md

Este proyecto **todavía no tiene sustrato**. Antes de ponerte a tocar código,
móntalo — no dejes el pendiente en prosa "solo por esta vez":

```bash
npm i -D backlog.md@1.50.1   # o npx backlog directamente si no hay package.json
npx backlog init
```

Checklist completo en `~/atalaya/docs/runbooks/replicar-sustrato.md` (10 pasos,
incluido el que más se olvida: mergear a la rama por defecto el mismo día).

El reparto que hay que dejar montado, y que a partir de entonces manda:

- `backlog/tasks/` — **lo pendiente**. Se muta con la CLI, nunca a mano.
- `docs/decisions/NNNN-*.md` — **por qué** se decidió algo. Un fichero por
  decisión, inmutable salvo para marcar `Superseded by`.
- `docs/design/*.md` y `docs/ARCHITECTURE.md` — cómo funciona **hoy**, sin
  historia.

Nada de listas de pendiente en `docs/`, ni en GitHub Issues
(`atalaya` `decisions/0010`). La CLI crea `backlog/decisions/`, `backlog/docs/`
y `backlog/milestones/`: no se usan.

Decidido el 2026-08-23 · `atalaya` `decisions/0009`, `0010` y `0011`.

### Qué migrar cuando llegue el momento

Este repo ya tiene medio reparto montado: `docs/ARCHITECTURE.md` y ocho ADRs en
`docs/decisions/`. No hay fichero de pendiente que migrar — solo hay que hacer
`backlog init` y crear las tareas de lo que quede por hacer antes de empezar.
