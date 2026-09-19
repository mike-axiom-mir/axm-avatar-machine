from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import write_comparison
from .glb import inspect_glb
from .pipeline import run_pipeline
from .profile import load_profile


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="axm-avatar")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("profile", help="show the implemented Doll Profile v1")
    inspect = commands.add_parser("inspect-glb", help="decode GLB structure without Blender")
    inspect.add_argument("path")
    build = commands.add_parser("build", help="run the common Doll Profile v1 pipeline")
    build.add_argument("request")
    build.add_argument("output")
    build.add_argument("--blender")
    build.add_argument("--bpy-python")
    build.add_argument("--timeout-seconds", type=int, default=1800)
    compare = commands.add_parser("benchmark", help="compare a generated result with the historical fixture")
    compare.add_argument("historical")
    compare.add_argument("generated")
    compare.add_argument("output")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "profile":
        value = load_profile()
    elif args.command == "inspect-glb":
        value = inspect_glb(args.path)
    elif args.command == "build":
        value = run_pipeline(
            args.request,
            args.output,
            blender=args.blender,
            bpy_python=args.bpy_python,
            timeout_seconds=args.timeout_seconds,
        )
    else:
        value = write_comparison(args.historical, args.generated, Path(args.output))
    print(json.dumps(value, indent=2))
    return 0
