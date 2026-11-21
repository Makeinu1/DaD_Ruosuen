#!/usr/bin/env python3
"""Derive physically-based Cycles textures (Albedo, Normal, Roughness, Height, RGBA Petal, Caustics) for V5 Cinema Look-Dev."""

from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ART_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p/4733e009-f44e-4728-af83-1f85c37a4d1d")
TEX_DIR = Path("dm/episode-01/ending/video-pipeline/v5_cycles/textures")
TEX_DIR.mkdir(parents=True, exist_ok=True)


def find_art(prefix: str) -> Path:
    matches = sorted(ART_DIR.glob(f"{prefix}*.jpg")) + sorted(ART_DIR.glob(f"{prefix}*.png"))
    assert matches, f"Missing artifact starting with {prefix}"
    return matches[-1]


def make_seamless_blend(arr: np.ndarray, margin: int = 64) -> np.ndarray:
    """Ensure perfectly periodic edges for tileable PBR maps using cosine crossfade on wrapped borders."""
    h, w = arr.shape[:2]
    # Shift by half, blend seams cleanly
    out = arr.copy()
    rolled_x = np.roll(out, w // 2, axis=1)
    t = np.linspace(0, np.pi, margin, dtype=np.float32)
    w_edge = (0.5 - 0.5 * np.cos(t)).reshape(1, margin, 1) if arr.ndim == 3 else (0.5 - 0.5 * np.cos(t)).reshape(1, margin)
    # Only lightly harmonize outermost border strip to preserve photographic rock continuity
    strip = margin // 2
    t2 = (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, strip, dtype=np.float32)))
    if arr.ndim == 3:
        t2_x = t2.reshape(1, strip, 1)
        t2_y = t2.reshape(strip, 1, 1)
    else:
        t2_x = t2.reshape(1, strip)
        t2_y = t2.reshape(strip, 1)
    left_right_avg = 0.5 * (out[:, :strip] + out[:, -strip:][:, ::-1])
    out[:, :strip] = out[:, :strip] * t2_x + left_right_avg * (1.0 - t2_x)
    out[:, -strip:] = out[:, -strip:] * t2_x[:, ::-1] + left_right_avg[:, ::-1] * (1.0 - t2_x[:, ::-1])
    top_bot_avg = 0.5 * (out[:strip, :] + out[-strip:, :][::-1, :])
    out[:strip, :] = out[:strip, :] * t2_y + top_bot_avg * (1.0 - t2_y)
    out[-strip:, :] = out[-strip:, :] * t2_y[::-1, :] + top_bot_avg[::-1, :] * (1.0 - t2_y[::-1, :])
    return out


def height_to_normal(height: np.ndarray, strength: float = 4.0) -> np.ndarray:
    """Periodic Sobel normal map in OpenGL tangent space."""
    h = height.astype(np.float32)
    dx = (
        np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)
        + 0.5 * (np.roll(np.roll(h, -1, axis=1), -1, axis=0) - np.roll(np.roll(h, 1, axis=1), -1, axis=0))
        + 0.5 * (np.roll(np.roll(h, -1, axis=1), 1, axis=0) - np.roll(np.roll(h, 1, axis=1), 1, axis=0))
    ) * strength
    dy = (
        np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)
        + 0.5 * (np.roll(np.roll(h, -1, axis=0), -1, axis=1) - np.roll(np.roll(h, 1, axis=0), -1, axis=1))
        + 0.5 * (np.roll(np.roll(h, -1, axis=0), 1, axis=1) - np.roll(np.roll(h, 1, axis=0), 1, axis=1))
    ) * strength
    nx = -dx
    ny = dy
    nz = np.ones_like(h)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    rgb = np.stack([nx / norm * 0.5 + 0.5, ny / norm * 0.5 + 0.5, nz / norm * 0.5 + 0.5], axis=-1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


def build_basalt_pbr():
    im = Image.open(find_art("v5_tex_wet_basalt")).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    arr = make_seamless_blend(arr, margin=48)

    # Detect moss crevices (higher green relative to red)
    moss_mask = np.clip((arr[:, :, 1] - arr[:, :, 0] * 1.04) * 5.0, 0.0, 1.0)

    # Cool nocturnal subterranean grading: dark volcanic slate-blue-charcoal stone + deep wet emerald moss
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    cool_stone = np.stack([
        arr[:, :, 0] * 0.62 + lum * 0.08,
        arr[:, :, 1] * 0.68 + lum * 0.11,
        arr[:, :, 2] * 0.80 + lum * 0.16,
    ], axis=-1)
    moss_tint = np.stack([
        arr[:, :, 0] * 0.45,
        arr[:, :, 1] * 0.78,
        arr[:, :, 2] * 0.62,
    ], axis=-1)
    albedo = cool_stone * (1.0 - moss_mask[..., None]) + moss_tint * moss_mask[..., None]
    albedo = np.clip(albedo * 0.82, 0.015, 0.92)
    Image.fromarray((albedo * 255).astype(np.uint8)).save(TEX_DIR / "basalt_albedo.png")

    # Height map: rock relief + deeper cracks
    h_raw = np.clip((lum - 0.08) / 0.72, 0.0, 1.0)
    h_smooth = np.asarray(Image.fromarray((h_raw * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    height = np.clip(h_raw * 0.65 + h_smooth * 0.35 - moss_mask * 0.15, 0.0, 1.0)
    Image.fromarray((height * 255).astype(np.uint8)).save(TEX_DIR / "basalt_height.png")

    # Normal map (crisp geological facets!)
    normal = height_to_normal(height, strength=5.5)
    Image.fromarray(normal).save(TEX_DIR / "basalt_normal.png")

    # Wet cavern roughness: damp glossy water-streaked ridges (0.14..0.38), matte crevices & moss (0.72..0.88)
    h_res, w_res = height.shape
    x = np.linspace(0, 2 * np.pi, w_res, dtype=np.float32)
    y = np.linspace(0, 2 * np.pi, h_res, dtype=np.float32)
    xg, yg = np.meshgrid(x, y)
    wet_streaks = 0.5 + 0.5 * np.sin(xg * 7.0 + np.sin(yg * 2.0 + xg * 3.0) * 1.4)
    wet_streaks = np.clip((wet_streaks - 0.35) * 1.6, 0.0, 1.0)
    rough = 0.56 - height * 0.28 - wet_streaks * 0.16 + moss_mask * 0.36
    rough = np.clip(rough, 0.11, 0.90)
    Image.fromarray((rough * 255).astype(np.uint8)).save(TEX_DIR / "basalt_roughness.png")
    print(f"[PBR] Built basalt maps ({w_res}x{h_res})")


def build_petal_pbr():
    im = Image.open(find_art("v5_tex_flower_petal")).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    lum = np.max(arr, axis=-1)
    # Clean crisp botanical alpha from pure pitch-black studio backdrop
    alpha = np.clip((lum - 0.035) / 0.11, 0.0, 1.0)
    # Slightly soften edge by 0.6px for anti-aliased Cycles transparency
    alpha_im = Image.fromarray((alpha * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    alpha = np.asarray(alpha_im, dtype=np.float32) / 255.0
    # Unpremultiply near silhouette to prevent dark fringes
    rgb_clean = np.where(alpha[..., None] > 0.08, np.clip(arr / np.maximum(alpha[..., None], 0.25), 0.0, 1.0), np.array([0.96, 0.94, 0.90], dtype=np.float32))
    # Gentle warm luminous ivory-pearl lift
    rgb_clean = np.clip(rgb_clean * 1.05, 0.0, 1.0)
    rgba = np.concatenate([rgb_clean, alpha[..., None]], axis=-1)
    Image.fromarray((rgba * 255).astype(np.uint8), mode="RGBA").save(TEX_DIR / "petal_rgba.png")

    # Fine vein bump map
    gray = 0.3 * arr[:, :, 0] + 0.59 * arr[:, :, 1] + 0.11 * arr[:, :, 2]
    blur = np.asarray(Image.fromarray((gray * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.0)), dtype=np.float32) / 255.0
    veins = np.clip(0.5 + (gray - blur) * 4.0, 0.0, 1.0) * alpha + 0.5 * (1.0 - alpha)
    Image.fromarray((veins * 255).astype(np.uint8)).save(TEX_DIR / "petal_bump.png")
    print(f"[PBR] Built translucent petal RGBA + bump ({im.size})")


def build_whale_pbr():
    im = Image.open(find_art("v5_tex_whale_skin")).convert("RGB")
    arr = np.asarray(im, dtype=np.float32) / 255.0
    arr = make_seamless_blend(arr, margin=48)
    Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(TEX_DIR / "whale_skin_albedo.png")

    # Subtle micro-grain & vertical water-film streaks (zero bumps/tubercles!)
    gray = 0.3 * arr[:, :, 0] + 0.59 * arr[:, :, 1] + 0.11 * arr[:, :, 2]
    blur = np.asarray(Image.fromarray((gray * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4.0)), dtype=np.float32) / 255.0
    fine = np.clip(0.5 + (gray - blur) * 3.0, 0.0, 1.0)
    Image.fromarray((fine * 255).astype(np.uint8)).save(TEX_DIR / "whale_skin_bump.png")

    # Wet glossy rivulets (0.07) vs satin moist cetacean skin (0.24)
    rough = np.clip(0.24 - np.abs(gray - blur) * 1.8 - (gray - 0.5) * 0.08, 0.06, 0.32)
    Image.fromarray((rough * 255).astype(np.uint8)).save(TEX_DIR / "whale_skin_roughness.png")
    print(f"[PBR] Built smooth whale skin maps ({im.size})")


def build_moon_and_caustics():
    moon_src = find_art("v5_tex_moon_sky")
    im = Image.open(moon_src).convert("RGB")
    im.save(TEX_DIR / "moon_sky.png")
    print(f"[PBR] Copied moon sky ({im.size})")

    # Seamless 512x512 optical water-caustic cellular network for light gobo projection!
    n = 512
    rng = np.random.default_rng(42)
    pts = rng.random((42, 2))
    ys, xs = np.mgrid[0:n, 0:n] / float(n)
    d1 = np.full((n, n), 9.0, dtype=np.float32)
    d2 = np.full((n, n), 9.0, dtype=np.float32)
    for px, py in pts:
        dx = np.abs(xs - px)
        dx = np.minimum(dx, 1.0 - dx)
        dy = np.abs(ys - py)
        dy = np.minimum(dy, 1.0 - dy)
        dist = np.sqrt(dx * dx + dy * dy).astype(np.float32)
        mask = dist < d1
        d2 = np.where(mask, d1, np.minimum(d2, dist))
        d1 = np.where(mask, dist, d1)
    ridge = np.exp(-((d2 - d1) * 28.0) ** 2)
    # Add second harmonic caustic shimmer
    ridge2 = np.roll(np.roll(ridge, 97, axis=0), 173, axis=1)
    caustic = np.clip(ridge * 0.75 + ridge2 * 0.45, 0.0, 1.0) ** 1.35
    caustic_rgb = np.stack([caustic * 0.72, caustic * 0.88, caustic * 1.0], axis=-1)
    Image.fromarray((np.clip(caustic_rgb, 0, 1) * 255).astype(np.uint8)).save(TEX_DIR / "water_caustics.png")
    print("[PBR] Built tileable water caustics gobo (512x512)")


if __name__ == "__main__":
    build_basalt_pbr()
    build_petal_pbr()
    build_whale_pbr()
    build_moon_and_caustics()
    print("[DONE] All V5 PBR textures ready!")
