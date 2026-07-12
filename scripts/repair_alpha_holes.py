"""Fill transparency holes enclosed inside an extracted character matte.

Chroma-key extraction can mistake dark costume details for the dark source
background. This keeps all transparency connected to the canvas edge while
restoring enclosed pixels to fully opaque.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image


def repair(image: Image.Image, threshold: int = 128) -> Image.Image:
    pixels = np.asarray(image.convert("RGBA")).copy()
    alpha = pixels[..., 3]
    passable = alpha < threshold
    outside = np.zeros(passable.shape, dtype=bool)
    height, width = passable.shape
    queue: deque[tuple[int, int]] = deque()

    for x in range(width):
        for y in (0, height - 1):
            if passable[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))
    for y in range(height):
        for x in (0, width - 1):
            if passable[y, x] and not outside[y, x]:
                outside[y, x] = True
                queue.append((y, x))

    while queue:
        y, x = queue.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if (
                0 <= ny < height
                and 0 <= nx < width
                and passable[ny, nx]
                and not outside[ny, nx]
            ):
                outside[ny, nx] = True
                queue.append((ny, nx))

    enclosed = (~outside) & (alpha < 255)
    pixels[..., 3][enclosed] = 255
    return Image.fromarray(pixels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(args.input_dir.glob("*.png")):
        output = args.output_dir / path.name
        repair(Image.open(path)).save(output)
        print(f"Repaired {output}")


if __name__ == "__main__":
    main()
