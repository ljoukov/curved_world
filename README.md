# Curved World

Concept screens for strange educational software from slightly incompatible universes.

## Run the prototype

```sh
npm install
npm run dev
```

The SvelteKit prototype recreates the Curved World lesson UI and includes local demo interactions. Realtime voice is intentionally left as a later integration.

## Concepts

### Curved World

An online geometry tutor from a hyperbolic universe, where Euclidean geometry is treated as a medical emergency.

![Curved World lesson](concept-screens/curved-world/01-lesson.png)

![Curved World diagnosis](concept-screens/curved-world/02-diagnosis.png)

### Professor Stare

An applied-object-permanence course where classroom objects exist only while someone is watching them.

![Professor Stare observed state](concept-screens/professor-stare/01-observed.png)

![Professor Stare unobserved state](concept-screens/professor-stare/02-unobserved.png)

### The Backwards Academy

A surreal school where answers arrive before their questions.

![Backwards Academy lesson](concept-screens/backwards-academy/01-lesson.png)

![Backwards Academy diploma](concept-screens/backwards-academy/02-diploma.png)

### Professor Tomorrow

A reverse-causality classroom where consequences happen before their causes.

![Professor Tomorrow failing grade](concept-screens/professor-tomorrow/01-failing-grade.png)

![Professor Tomorrow retroactive A+](concept-screens/professor-tomorrow/02-retroactive-a-plus.png)

The complete image-generation prompts are in [concept-screens/PROMPTS.md](concept-screens/PROMPTS.md).

## Professor Bent animation assets

Professor Bent now has a dedicated speaking loop, a set of emotional reaction
frames, and a rigged 3D version. The raster loops are ready to use in an
ordinary `<img>` element; the GLB includes `Idle`, `Talk`, `Point`, and `Think`
animation clips.

![Professor Bent speaking](assets/professor-bent/professor-bent-main-loop.webp)

![Professor Bent expression loop](assets/professor-bent/professor-bent-loop.webp)

![Professor Bent 3D preview](assets/professor-bent/professor-bent-preview.png)

See [the asset notes](assets/professor-bent/README.md) for individual frames,
Three.js loading, and regeneration instructions.
