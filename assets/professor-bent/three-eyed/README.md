# Three-eyed Professor Bent sprites

Every image in this directory has a transparent background. All individual
frames use the same 512 by 640 canvas so the app can swap them without layout
changes.

## Talking loop

The eight eye-aligned mouth frames are under `talking/`. Their order and a
110 ms default frame duration are recorded in `manifest.json`.

`talking-loop.png` is an animated PNG preview of the same sequence. The three
pupil centers were detected independently in every source frame, then mapped
to one shared three-point anchor. `alignment-report.json` records the detected
coordinates and final registration error.

## Expressions

The eight independent reaction frames are under `expressions/`:

1. neutral attentive
2. warm happy
3. delighted
4. surprised
5. concerned
6. skeptical
7. thinking
8. reassuring

These frames intentionally preserve their natural eye and head movement and
were not eye-aligned.

## Regeneration

The generated sprite sheets were keyed against a flat magenta background and
converted to RGBA with the installed imagegen chroma-removal helper. Rebuild
the cropped frames, alignment report, manifest, and animated preview with:

```sh
/Users/yaroslavvolovich/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  scripts/process_professor_bent_three_eyed.py
```

