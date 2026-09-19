#!/usr/bin/env python3
"""Render selected review frames or the full Odd Shift Duo animation."""

import argparse
import sys
from pathlib import Path

import bpy


def args():
    tail = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--blend")
    parser.add_argument("--output", required=True)
    parser.add_argument("--frames", default="")
    parser.add_argument("--animation", action="store_true")
    parser.add_argument("--width", type=int, default=720)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--step", type=int, default=1)
    return parser.parse_args(tail)


def main():
    cfg = args()
    if cfg.blend:
        bpy.ops.wm.open_mainfile(filepath=str(Path(cfg.blend).resolve()))
    output = Path(cfg.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = cfg.width
    scene.render.resolution_y = cfg.height
    scene.render.resolution_percentage = 100
    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = cfg.samples
    if cfg.animation:
        scene.frame_step = cfg.step
        scene.render.fps = max(1, round(scene.render.fps / cfg.step))
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.ffmpeg_preset = "GOOD"
        scene.render.ffmpeg.audio_codec = "NONE"
        scene.render.filepath = str(output / "Odd-Shift-Duo-Preview.mp4")
        bpy.ops.render.render(animation=True)
        return
    scene.render.image_settings.file_format = "PNG"
    for frame in [int(value) for value in cfg.frames.split(",") if value.strip()]:
        scene.frame_set(frame)
        scene.render.filepath = str(output / f"review_{frame:03d}.png")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
