#!/usr/bin/env python3
"""Build transparent, animation-ready three-eyed Professor Bent frame sets."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "assets" / "professor-bent" / "three-eyed"
TALKING_SHEET = ASSET_DIR / "talking-sheet-transparent.png"
EXPRESSIONS_SHEET = ASSET_DIR / "expressions-sheet-transparent.png"
TALKING_DIR = ASSET_DIR / "talking"
EXPRESSIONS_DIR = ASSET_DIR / "expressions"

CANVAS_SIZE = (512, 640)

TALKING_NAMES = (
    "01-mouth-closed.png",
    "02-mouth-small-open.png",
    "03-mouth-ah.png",
    "04-mouth-ee.png",
    "05-mouth-oh.png",
    "06-mouth-oo.png",
    "07-mouth-fv.png",
    "08-mouth-return.png",
)

EXPRESSION_NAMES = (
    "01-neutral-attentive.png",
    "02-warm-happy.png",
    "03-delighted.png",
    "04-surprised.png",
    "05-concerned.png",
    "06-skeptical.png",
    "07-thinking.png",
    "08-reassuring.png",
)

# Expected pupil positions as fractions of a talking cell. The detector searches
# only a compact neighborhood around each point, so dark costume and mouth pixels
# cannot be mistaken for eyes.
EYE_SEEDS = {
    "upper": (0.389, 0.294),
    "lower_left": (0.300, 0.415),
    "lower_right": (0.489, 0.415),
}


def split_sheet(path: Path, columns: int = 4, rows: int = 2) -> list[Image.Image]:
    sheet = Image.open(path).convert("RGBA")
    x_edges = [round(i * sheet.width / columns) for i in range(columns + 1)]
    y_edges = [round(i * sheet.height / rows) for i in range(rows + 1)]
    frames: list[Image.Image] = []
    for row in range(rows):
        for column in range(columns):
            frame = sheet.crop(
                (
                    x_edges[column],
                    y_edges[row],
                    x_edges[column + 1],
                    y_edges[row + 1],
                )
            )
            # Generated sprite sheets can leave a faint antialiased rule exactly
            # on a row boundary. No subject pixels occur in these top rows.
            rgba = np.array(frame, copy=True)
            rgba[:5, :, :] = 0
            frame = Image.fromarray(rgba, "RGBA")
            frames.append(frame)
    return frames


def pad_to_common_size(frames: list[Image.Image]) -> list[Image.Image]:
    width = max(frame.width for frame in frames)
    height = max(frame.height for frame in frames)
    padded: list[Image.Image] = []
    for frame in frames:
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.alpha_composite(frame, (0, 0))
        padded.append(canvas)
    return padded


def detect_pupil(frame: Image.Image, seed: tuple[float, float]) -> tuple[float, float]:
    rgba = np.asarray(frame, dtype=np.float64)
    height, width = rgba.shape[:2]
    expected_x = seed[0] * width
    expected_y = seed[1] * height
    radius_x = max(13, round(width * 0.041))
    radius_y = max(15, round(height * 0.043))
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


def detect_three_pupils(frame: Image.Image) -> dict[str, tuple[float, float]]:
    return {name: detect_pupil(frame, seed) for name, seed in EYE_SEEDS.items()}


def affine_from_points(
    source: dict[str, tuple[float, float]],
    target: dict[str, tuple[float, float]],
) -> np.ndarray:
    names = ("upper", "lower_left", "lower_right")
    src = np.array([[*source[name], 1.0] for name in names], dtype=np.float64)
    dst = np.array([target[name] for name in names], dtype=np.float64)
    coefficients = np.linalg.solve(src, dst)
    matrix = np.array(
        [
            [coefficients[0, 0], coefficients[1, 0], coefficients[2, 0]],
            [coefficients[0, 1], coefficients[1, 1], coefficients[2, 1]],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    return matrix


def transform_to_target(frame: Image.Image, forward: np.ndarray) -> Image.Image:
    inverse = np.linalg.inv(forward)
    coefficients = tuple(inverse[:2, :].reshape(-1))
    return frame.transform(
        frame.size,
        Image.Transform.AFFINE,
        data=coefficients,
        resample=Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0, 0),
    )


def contain_on_canvas(frame: Image.Image, size: tuple[int, int] = CANVAS_SIZE) -> Image.Image:
    scale = min(size[0] / frame.width, size[1] / frame.height)
    resized_size = (round(frame.width * scale), round(frame.height * scale))
    resized = frame.resize(resized_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    offset = ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas


def remove_residual_magenta(frame: Image.Image) -> Image.Image:
    """Drop the few strongly key-colored edge pixels left by soft matting."""
    rgba = np.array(frame.convert("RGBA"), copy=True)
    rgb = rgba[..., :3].astype(np.int16)
    alpha = rgba[..., 3]
    strongly_key_colored = (
        (rgb[..., 0] > 210)
        & (rgb[..., 1] < 90)
        & (rgb[..., 2] > 175)
        & ((np.minimum(rgb[..., 0], rgb[..., 2]) - rgb[..., 1]) > 115)
    )
    alpha[strongly_key_colored] = 0
    rgba[..., 3] = alpha
    rgba[alpha == 0, :3] = 0
    return Image.fromarray(rgba, "RGBA")


def assert_transparent(frame: Image.Image, name: str) -> dict[str, int | float]:
    rgba = np.asarray(frame.convert("RGBA"))
    alpha = rgba[..., 3]
    if any(alpha[y, x] != 0 for x, y in ((0, 0), (frame.width - 1, 0), (0, frame.height - 1), (frame.width - 1, frame.height - 1))):
        raise RuntimeError(f"{name} does not have transparent corners")
    transparent = int(np.count_nonzero(alpha == 0))
    partial = int(np.count_nonzero((alpha > 0) & (alpha < 255)))
    opaque_or_partial = alpha > 0
    rgb = rgba[..., :3]
    magenta_residue = int(
        np.count_nonzero(
            opaque_or_partial
            & (rgb[..., 0] > 220)
            & (rgb[..., 1] < 70)
            & (rgb[..., 2] > 190)
        )
    )
    if magenta_residue > 12:
        raise RuntimeError(f"{name} retains {magenta_residue} chroma-key pixels")
    return {
        "transparent_pixels": transparent,
        "partially_transparent_pixels": partial,
        "magenta_residue_pixels": magenta_residue,
        "transparent_fraction": round(transparent / alpha.size, 4),
    }


def main() -> None:
    TALKING_DIR.mkdir(parents=True, exist_ok=True)
    EXPRESSIONS_DIR.mkdir(parents=True, exist_ok=True)

    # Keep the retained sprite sheets transparent and free of chroma-key fringe too.
    for sheet_path in (TALKING_SHEET, EXPRESSIONS_SHEET):
        cleaned_sheet = remove_residual_magenta(Image.open(sheet_path).convert("RGBA"))
        cleaned_sheet.save(sheet_path, optimize=True)

    talking_frames = pad_to_common_size(split_sheet(TALKING_SHEET))
    detections = [detect_three_pupils(frame) for frame in talking_frames]
    canonical = {
        name: (
            float(np.median([detected[name][0] for detected in detections])),
            float(np.median([detected[name][1] for detected in detections])),
        )
        for name in EYE_SEEDS
    }

    report: dict[str, object] = {
        "canvas_size": list(CANVAS_SIZE),
        "talking_frames": [],
        "expression_frames": [],
    }

    aligned_native: list[Image.Image] = []
    for index, (frame, filename, detected) in enumerate(zip(talking_frames, TALKING_NAMES, detections), start=1):
        forward = affine_from_points(detected, canonical)
        aligned = transform_to_target(frame, forward)
        aligned_native.append(aligned)
        final = remove_residual_magenta(contain_on_canvas(aligned))
        output = TALKING_DIR / filename
        final.save(output, optimize=True)
        qa = assert_transparent(final, filename)
        transformed = {
            name: tuple((forward @ np.array([*point, 1.0]))[:2])
            for name, point in detected.items()
        }
        max_eye_error = max(
            float(np.hypot(transformed[name][0] - canonical[name][0], transformed[name][1] - canonical[name][1]))
            for name in canonical
        )
        report["talking_frames"].append(
            {
                "index": index,
                "file": f"talking/{filename}",
                "detected_pupils_before_alignment": {name: [round(x, 3), round(y, 3)] for name, (x, y) in detected.items()},
                "maximum_eye_registration_error_native_pixels": round(max_eye_error, 6),
                **qa,
            }
        )

    expression_frames = split_sheet(EXPRESSIONS_SHEET)
    for index, (frame, filename) in enumerate(zip(expression_frames, EXPRESSION_NAMES), start=1):
        final = remove_residual_magenta(contain_on_canvas(frame))
        output = EXPRESSIONS_DIR / filename
        final.save(output, optimize=True)
        report["expression_frames"].append(
            {
                "index": index,
                "file": f"expressions/{filename}",
                **assert_transparent(final, filename),
            }
        )

    redetected = [
        detect_three_pupils(Image.open(TALKING_DIR / name).convert("RGBA"))
        for name in TALKING_NAMES
    ]
    final_median = {
        name: np.median([frame[name] for frame in redetected], axis=0)
        for name in EYE_SEEDS
    }
    maximum_redetected_drift = max(
        float(np.linalg.norm(np.array(frame[name]) - final_median[name]))
        for frame in redetected
        for name in EYE_SEEDS
    )
    if maximum_redetected_drift >= 1.0:
        raise RuntimeError(
            f"Talking-frame eye drift is {maximum_redetected_drift:.3f} px"
        )
    report["summary"] = {
        "talking_frame_count": len(TALKING_NAMES),
        "expression_frame_count": len(EXPRESSION_NAMES),
        "maximum_redetected_pupil_drift_pixels": round(maximum_redetected_drift, 3),
        "maximum_allowed_pupil_drift_pixels": 1.0,
        "magenta_residue_pixels": 0,
    }

    loop_frames = [Image.open(TALKING_DIR / name).convert("RGBA") for name in TALKING_NAMES]
    stale_webp = ASSET_DIR / "talking-loop.webp"
    stale_webp.unlink(missing_ok=True)
    loop_frames[0].save(
        ASSET_DIR / "talking-loop.png",
        save_all=True,
        append_images=loop_frames[1:],
        duration=110,
        loop=0,
        disposal=2,
        blend=0,
        optimize=True,
    )

    manifest = {
        "canvas": {"width": CANVAS_SIZE[0], "height": CANVAS_SIZE[1]},
        "talking": {
            "frameDurationMs": 110,
            "loop": True,
            "frames": [f"talking/{name}" for name in TALKING_NAMES],
            "preview": "talking-loop.png",
        },
        "expressions": {
            "frames": [f"expressions/{name}" for name in EXPRESSION_NAMES],
        },
    }
    (ASSET_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ASSET_DIR / "alignment-report.json").write_text(json.dumps(report, indent=2) + "\n")

    # Verify the animated preview also preserves alpha.
    preview = Image.open(ASSET_DIR / "talking-loop.png").convert("RGBA")
    assert_transparent(preview, "talking-loop.png")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
