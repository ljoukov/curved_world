# Professor Bent assets

Two animation-ready versions of the Curved World professor live here.

## Three-eyed character sprites

The current world-canon version is under `three-eyed/`. It contains two fully
transparent, consistently named 512 by 640 PNG sets:

- `three-eyed/talking/` — eight mouth shapes with all three pupils registered
  to the same anchor
- `three-eyed/expressions/` — eight independent emotional reactions

`three-eyed/manifest.json` gives the frame order and default timing, while
`three-eyed/talking-loop.png` is a transparent animated PNG preview. See
`three-eyed/README.md` for the complete inventory and regeneration command.

## Main speaking animation

`professor-bent-main-loop.webp` is the primary in-app animation. It has a
transparent background and cycles through six mouth shapes at 5.6 frames per
second while keeping the professor's friendly expression, gaze, pose, and
costume stable:

```html
<img
  src="/assets/professor-bent/professor-bent-main-loop.webp"
  alt="Professor Bent speaking"
  width="557"
  height="470"
/>
```

The final transparent PNG frames are under `speaking-aligned/`. Their two eye
centers are aligned to within a fraction of a pixel; `eye-alignment.json`
records every detected eye pair and similarity transform. The raw unaligned
crops remain under `speaking/`, and the original 3-by-2 imagegen output is
`professor-bent-speaking-sheet.png`.

The alignment is reproducible with `scripts/align_speaking_frames.py`. The
background matte uses the installed imagegen chroma-removal helper, followed
by `scripts/repair_alpha_holes.py` to preserve dark costume details enclosed
inside the character silhouette.

## Emotion loop

`professor-bent-loop.webp` is the slower secondary reaction reel. It cycles
through eight different poses every 750 ms and loops indefinitely:

```html
<img
  src="/assets/professor-bent/professor-bent-loop.webp"
  alt="Professor Bent reacting"
  width="418"
  height="470"
/>
```

For application-controlled timing, use the eight PNGs under `sprites/` and
swap the `src` on an ordinary image element. The frame order is:

1. idle
2. talk
3. smile
4. surprised
5. point
6. think
7. concerned
8. reassure

The original 4-by-2 imagegen output is preserved as
`professor-bent-sprite-sheet.png`.

## 3D asset

- `professor-bent.glb` — web-ready glTF binary, 677 KB
- `professor-bent.blend` — editable Blender source
- `professor-bent-preview.png` — rendered preview
- `../../scripts/generate_professor_bent.py` — reproducible asset generator

The GLB contains four named animation clips: `Idle`, `Talk`, `Point`, and
`Think`. With Three.js, load and play a clip by name:

```js
const loader = new GLTFLoader();

loader.load('/assets/professor-bent/professor-bent.glb', (gltf) => {
  scene.add(gltf.scene);
  const mixer = new THREE.AnimationMixer(gltf.scene);
  const clip = THREE.AnimationClip.findByName(gltf.animations, 'Idle');
  mixer.clipAction(clip).play();
});
```

Regenerate the Blender, GLB, and preview files with:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --background \
  --python scripts/generate_professor_bent.py
```
