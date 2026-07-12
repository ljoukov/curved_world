"""Align Professor Bent speaking frames to a shared pair of eye anchors.

The eye detector uses the two largest cream-colored connected components in a
face-sized search region. A similarity transform then aligns both eye centers,
correcting translation, rotation, and scale without altering the artwork.

Requires Pillow and NumPy. The bundled Codex document runtime provides both.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def connected_components(mask: np.ndarray) -> list[np.ndarray]:
    seen = np.zeros(mask.shape, dtype=bool)
    components: list[np.ndarray] = []
    height, width = mask.shape
    for start_y, start_x in zip(*np.nonzero(mask)):
        if seen[start_y, start_x]:
            continue
        stack = [(int(start_y), int(start_x))]
        seen[start_y, start_x] = True
        points: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            points.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and mask[ny, nx]
                    and not seen[ny, nx]
                ):
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(points) >= 100:
            components.append(np.asarray(points, dtype=np.float64))
    return components


def detect_eyes(image: Image.Image) -> tuple[tuple[float, float], tuple[float, float]]:
    rgb = np.asarray(image.convert("RGB"))
    height, width = rgb.shape[:2]
    # The crop is intentionally broad enough for the original sheet's drift.
    x0, x1 = int(width * 0.10), int(width * 0.76)
    y0, y1 = int(height * 0.30), int(height * 0.53)
    roi = rgb[y0:y1, x0:x1].astype(np.int16)
    red, green, blue = roi[..., 0], roi[..., 1], roi[..., 2]
    # Isolate the warm cream eye whites while excluding teal skin and silver hair.
    mask = (
        (red > 150)
        & (green > 135)
        & (blue > 90)
        & ((red - blue) > 20)
        & ((green - blue) > 5)
    )
    components = connected_components(mask)
    if len(components) < 2:
        raise RuntimeError("Could not detect both eye-white components")
    eyes = []
    for component in sorted(components, key=len, reverse=True)[:2]:
        y = y0 + float(component[:, 0].mean())
        x = x0 + float(component[:, 1].mean())
        eyes.append((x, y))
    eyes.sort(key=lambda point: point[0])
    if not 65 <= eyes[1][0] - eyes[0][0] <= 100:
        raise RuntimeError(f"Implausible eye spacing: {eyes}")
    return eyes[0], eyes[1]


def similarity_coefficients(source_left, source_right, target_left, target_right):
    source_delta = complex(*source_right) - complex(*source_left)
    target_delta = complex(*target_right) - complex(*target_left)
    forward = target_delta / source_delta
    offset = complex(*target_left) - forward * complex(*source_left)
    inverse = 1.0 / forward
    inverse_offset = -inverse * offset
    # Pillow maps output coordinates back into the input image.
    return (
        inverse.real,
        -inverse.imag,
        inverse_offset.real,
        inverse.imag,
        inverse.real,
        inverse_offset.imag,
    ), abs(forward), np.degrees(np.angle(forward)), (offset.real, offset.imag)


def border_key(image: Image.Image) -> tuple[int, int, int]:
    rgb = np.asarray(image.convert("RGB"))
    border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]), axis=0)
    return tuple(int(value) for value in np.median(border, axis=0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()

    paths = sorted(args.input_dir.glob("*.png"))
    if not paths:
        raise SystemExit(f"No PNG frames found under {args.input_dir}")
    images = [Image.open(path).convert("RGB") for path in paths]
    eye_pairs = [detect_eyes(image) for image in images]
    target_left, target_right = eye_pairs[0]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    records = []
    for path, image, (left, right) in zip(paths, images, eye_pairs):
        coefficients, scale, angle, offset = similarity_coefficients(
            left, right, target_left, target_right
        )
        aligned = image.transform(
            image.size,
            Image.Transform.AFFINE,
            coefficients,
            resample=Image.Resampling.BICUBIC,
            fillcolor=border_key(image),
        )
        output_path = args.output_dir / path.name
        aligned.save(output_path)
        verified_left, verified_right = detect_eyes(aligned)
        records.append(
            {
                "frame": path.name,
                "source_eyes": [left, right],
                "aligned_eyes": [verified_left, verified_right],
                "target_eyes": [target_left, target_right],
                "scale": scale,
                "rotation_degrees": angle,
                "translation": offset,
            }
        )
        print(
            f"{path.name}: eyes {left!r}, {right!r}; "
            f"scale={scale:.5f}, rotation={angle:.3f} deg"
        )

    args.manifest.write_text(json.dumps({"frames": records}, indent=2) + "\n")


if __name__ == "__main__":
    main()
