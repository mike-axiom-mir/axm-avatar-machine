from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import write_comparison
from .blueprint import compile_blueprint_file, load_blueprint
from .blueprint_pipeline import build_blueprint
from .glb import inspect_glb
from .interpretation import resolve_interpretation, write_reference_packet
from .pipeline import run_pipeline
from .profile import load_profile


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="axm-avatar")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("profile", help="show the implemented recovered Doll Profile v1")
    inspect = commands.add_parser("inspect-glb", help="decode GLB structure without Blender")
    inspect.add_argument("path")

    build = commands.add_parser("build", help="run the recovered Odd Shift Doll Profile v1 pipeline")
    build.add_argument("request")
    build.add_argument("output")
    build.add_argument("--blender")
    build.add_argument("--bpy-python")
    build.add_argument("--timeout-seconds", type=int, default=1800)

    compare = commands.add_parser("benchmark", help="compare a generated result with the historical fixture")
    compare.add_argument("historical")
    compare.add_argument("generated")
    compare.add_argument("output")

    validate = commands.add_parser("validate-blueprint", help="validate bounded human/AI-authored Doll Blueprint v1")
    validate.add_argument("blueprint")

    compile_cmd = commands.add_parser("compile-blueprint", help="compile Doll Blueprint v1 to deterministic scene plan")
    compile_cmd.add_argument("blueprint")
    compile_cmd.add_argument("output")

    build_bp = commands.add_parser("build-blueprint", help="compile and build a Doll Blueprint v1 with Blender")
    build_bp.add_argument("blueprint")
    build_bp.add_argument("output")
    build_bp.add_argument("--blender")
    build_bp.add_argument("--bpy-python")
    build_bp.add_argument("--timeout-seconds", type=int, default=1800)

    packet = commands.add_parser(
        "reference-packet",
        help="copy/hash references into a portable packet for a human or optional replaceable interpreter",
    )
    packet.add_argument("output", help="new output directory containing reference-packet.json and reference bytes")
    packet.add_argument("images", nargs="+")

    interpret = commands.add_parser(
        "interpret-reference",
        help="validate a human/external interpretation response or call an explicit replaceable adapter",
    )
    interpret.add_argument("packet")
    interpret.add_argument("output")
    source = interpret.add_mutually_exclusive_group(required=True)
    source.add_argument("--response", help="existing interpretation-response JSON authored by a human or provider")
    source.add_argument("--adapter", help="executable adapter implementing the AXM interpretation protocol")
    interpret.add_argument("--timeout-seconds", type=int, default=300)
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
    elif args.command == "benchmark":
        value = write_comparison(args.historical, args.generated, Path(args.output))
    elif args.command == "validate-blueprint":
        value = load_blueprint(args.blueprint)
    elif args.command == "compile-blueprint":
        value = compile_blueprint_file(args.blueprint, args.output)
    elif args.command == "build-blueprint":
        value = build_blueprint(
            args.blueprint,
            args.output,
            blender=args.blender,
            bpy_python=args.bpy_python,
            timeout_seconds=args.timeout_seconds,
        )
    elif args.command == "reference-packet":
        value = write_reference_packet(args.images, args.output)
    else:
        value = resolve_interpretation(
            args.packet,
            args.output,
            response_path=args.response,
            adapter=args.adapter,
            timeout_seconds=args.timeout_seconds,
        )
    print(json.dumps(value, indent=2))
    return 0
