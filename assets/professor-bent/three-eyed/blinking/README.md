# Isolated eye-blink frames

This directory is self-contained and does not alter the existing talking or
expression manifests.

The six transparent 512 by 640 PNG frames show all three eyes moving through
one synchronized blink. `blink-loop.png` is an animated PNG preview, and
`manifest.json` records the frame order and per-frame timing.

The open frame is registered to the existing talking-frame eye anchor. Run
`process_frames.py` from the repository root to rebuild this isolated set.

