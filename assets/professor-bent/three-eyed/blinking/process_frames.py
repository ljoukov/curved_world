#!/usr/bin/env python3
"""Build the isolated transparent blink-frame set."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "talking" / "01-mouth-closed.png"
SHEET = HERE / "sheet-transparent.png"
CANVAS = (512, 640)

FRAME_NAMES = (
    "01-eyes-open.png",
    "02-blink-quarter.png",
    "03-blink-mostly-closed.png",
    "04-eyes-closed.png",
    "05-blink-opening.png",
    "06-blink-nearly-open.png",
)

FRAME_DURATIONS_MS = (700, 70, 70, 120, 70, 70)

TARGET_EYE_SEEDS = {
    "upper": (0.389, 0.305),
    "lower_left": (0.300, 0.420),
    "lower_right": (0.489, 0.420),
}

# The generated blink sheet places the same face slightly lower and farther
# right than the existing talking frames, so pupil detection starts from its
# own approximate triangle before the shared affine registration is applied.
SOURCE_EYE_SEEDS = {
    "upper": (0.430, 0.340),
    "lower_left": (0.350, 0.445),
    "lower_right": (0.530, 0.445),
}


def remove_residual_magenta(frame: Image.Image) -> Image.Image:
    rgba = np.array(frame.convert("RGBA"), copy=True)
    rgb = rgba[..., :3].astype(np.int16)
    alpha = rgba[..., 3]
    key = (
        (rgb[..., 0] > 205)
        & (rgb[..., 1] < 95)
        & (rgb[..., 2] > 170)
        & ((np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1]) > 105)
    )
    alpha[key] = 0
    rgba[..., 3] = alpha
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")


def split_sheet() -> list[Image.Image]:
    sheet = remove_residual_magenta(Image.open(SHEET).convert("RGBA"))
    sheet.save(SHEET, optimize=True)
    x_edges = [round(i * sheet.width / 3) for i in range(4)]
    y_edges = [round(i * sheet.height / 2) for i in range(3)]
    frames: list[Image.Image] = []
    for row in range(2):
        for column in range(3):
            frame = sheet.crop(
                (
                    x_edges[column],
                    y_edges[row],
                    x_edges[column + 1],
                    y_edges[row + 1],
                )
            )
            rgba = np.array(frame, copy=True)
            rgba[:5, :, :] = 0
            frame = Image.fromarray(rgba, "RGBA")
            canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
            scale = min(CANVAS[0] / frame.width, CANVAS[1] / frame.height)
            resized = frame.resize(
                (round(frame.width * scale), round(frame.height * scale)),
                Image.Resampling.LANCZOS,
            )
            canvas.alpha_composite(
                resized,
                ((CANVAS[0] - resized.width) // 2, (CANVAS[1] - resized.height) // 2),
            )
            frames.append(remove_residual_magenta(canvas))
    return frames


def detect_pupil(frame: Image.Image, seed: tuple[float, float]) -> tuple[float, float]:
    rgba = np.asarray(frame, dtype=np.float64)
    height, width = rgba.shape[:2]
    expected_x = seed[0] * width
    expected_y = seed[1] * height
    radius_x = 30
    radius_y = 34
    x0 = max(0, round(expected_x - radius_x))
    x1 = min(width, round(expected_x + radius_x + 1))
    y0 = max(0, round(expected_y - radius_y))
    y1 = min(height, round(expected_y + radius_y + 1))
    crop = rgba[y0:y1, x0:x1]
    rgb = crop[..., :3]
    alpha = crop[..., 3] / 255.0
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    darkness = np.clip((115.0 - luminance) / 115.0, 0.0, 1.0) ** 4
    warmth = np.clip((rgb[..., 0] - rgb[..., 2]) / 140.0, 0.0, 1.0)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    distance = ((xx - expected_x) / radius_x) ** 2 + ((yy - expected_y) / radius_y) ** 2
    center_prior = np.clip(1.0 - distance, 0.0, 1.0) ** 1.5
    weights = darkness * (0.45 + warmth) * center_prior * alpha
    total = float(weights.sum())
    if total < 0.25:
        raise RuntimeError(f"Pupil detection failed near {(expected_x, expected_y)}")
    return float((weights * xx).sum() / total), float((weights * yy).sum() / total)


def detect_three(
    frame: Image.Image,
    seeds: dict[str, tuple[float, float]] = TARGET_EYE_SEEDS,
) -> dict[str, tuple[float, float]]:
    return {name: detect_pupil(frame, seed) for name, seed in seeds.items()}


def affine_from_points(
    source: dict[str, tuple[float, float]],
    target: dict[str, tuple[float, float]],
) -> np.ndarray:
    names = ("upper", "lower_left", "lower_right")
    src = np.array([[*source[name], 1.0] for name in names], dtype=np.float64)
    dst = np.array([target[name] for name in names], dtype=np.float64)
    coefficients = np.linalg.solve(src, dst)
    return np.array(
        [
            [coefficients[0, 0], coefficients[1, 0], coefficients[2, 0]],
            [coefficients[0, 1], coefficients[1, 1], coefficients[2, 1]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )


def transform(frame: Image.Image, forward: np.ndarray) -> Image.Image:
    inverse = np.linalg.inv(forward)
    return frame.transform(
        CANVAS,
        Image.Transform.AFFINE,
        data=tuple(inverse[:2, :].reshape(-1)),
        resample=Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0, 0),
    )


def upper_body_centroid(frame: Image.Image) -> tuple[float, float]:
    """Return a stable face/hair centroid, excluding variable lower crop edges."""
    alpha = np.asarray(frame, dtype=np.float64)[:400, :, 3] / 255.0
    yy, xx = np.mgrid[: alpha.shape[0], : alpha.shape[1]]
    total = float(alpha.sum())
    if total <= 0:
        raise RuntimeError("Cannot align an empty blink frame")
    return float((alpha * xx).sum() / total), float((alpha * yy).sum() / total)


def validate(frame: Image.Image, name: str) -> dict[str, float | int]:
    if frame.mode != "RGBA" or frame.size != CANVAS:
        raise RuntimeError(f"{name} has unexpected mode or size")
    rgba = np.asarray(frame)
    alpha = rgba[..., 3]
    if any(alpha[y, x] != 0 for x, y in ((0, 0), (511, 0), (0, 639), (511, 639))):
        raise RuntimeError(f"{name} lacks transparent corners")
    residue = (
        (alpha > 0)
        & (rgba[..., 0] > 220)
        & (rgba[..., 1] < 70)
        & (rgba[..., 2] > 190)
    )
    residue_count = int(np.count_nonzero(residue))
    if residue_count:
        raise RuntimeError(f"{name} retains {residue_count} key-colored pixels")
    return {
        "transparent_fraction": round(float(np.mean(alpha == 0)), 4),
        "magenta_residue_pixels": residue_count,
    }


def main() -> None:
    frames = split_sheet()
    source_pupils = detect_three(frames[0], SOURCE_EYE_SEEDS)
    reference = Image.open(REFERENCE).convert("RGBA")
    target_pupils = detect_three(reference)
    forward = affine_from_points(source_pupils, target_pupils)

    report: dict[str, object] = {
        "canvas": list(CANVAS),
        "source_open_eye_centers": {name: [round(x, 3), round(y, 3)] for name, (x, y) in source_pupils.items()},
        "target_talking_eye_centers": {name: [round(x, 3), round(y, 3)] for name, (x, y) in target_pupils.items()},
        "frames": [],
    }

    # The image-generation sheet has a consistent per-column horizontal drift.
    # Register every cell to frame zero after the shared three-eye transform,
    # then combine both transforms so each final frame is resampled only once.
    rough_outputs = [remove_residual_magenta(transform(frame, forward)) for frame in frames]
    target_centroid = upper_body_centroid(rough_outputs[0])

    outputs: list[Image.Image] = []
    for name, frame, rough in zip(FRAME_NAMES, frames, rough_outputs):
        centroid = upper_body_centroid(rough)
        dx = target_centroid[0] - centroid[0]
        dy = target_centroid[1] - centroid[1]
        correction = np.array(
            [[1.0, 0.0, dx], [0.0, 1.0, dy], [0.0, 0.0, 1.0]],
            dtype=np.float64,
        )
        aligned = remove_residual_magenta(transform(frame, correction @ forward))
        aligned.save(HERE / name, optimize=True)
        outputs.append(aligned)
        report["frames"].append(
            {
                "file": name,
                "upper_body_alignment_offset": [round(dx, 3), round(dy, 3)],
                "upper_body_centroid": [
                    round(upper_body_centroid(aligned)[0], 3),
                    round(upper_body_centroid(aligned)[1], 3),
                ],
                **validate(aligned, name),
            }
        )

    final_open = detect_three(outputs[0])
    maximum_open_eye_error = max(
        float(np.linalg.norm(np.array(final_open[name]) - np.array(target_pupils[name])))
        for name in target_pupils
    )
    if maximum_open_eye_error >= 1.5:
        raise RuntimeError(f"Open blink frame differs from talking anchor by {maximum_open_eye_error:.3f}px")
    report["maximum_open_eye_anchor_error_pixels"] = round(maximum_open_eye_error, 3)

    outputs[0].save(
        HERE / "blink-loop.png",
        save_all=True,
        append_images=outputs[1:],
        duration=list(FRAME_DURATIONS_MS),
        loop=0,
        disposal=2,
        blend=0,
        optimize=True,
    )
    manifest = {
        "isolated": True,
        "canvas": {"width": CANVAS[0], "height": CANVAS[1]},
        "frames": [
            {"file": name, "durationMs": duration}
            for name, duration in zip(FRAME_NAMES, FRAME_DURATIONS_MS)
        ],
        "preview": "blink-loop.png",
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (HERE / "alignment-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
