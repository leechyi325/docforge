from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from pydantic import TypeAdapter

from engine.diagnostics.diagnose import diagnose_docx
from engine.fixer.apply_fixes import apply_fixes
from engine.llm.client import create_llm_client
from engine.llm.settings import LlmSettings
from engine.models import Issue
from engine.pipeline import UnsupportedInputError, format_document
from engine.profiles.loader import load_profile


def _add_formatting_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", required=True)
    parser.add_argument("--profile", default="general")
    parser.add_argument("--format-instruction", default="")
    parser.add_argument(
        "--llm-provider",
        choices=[
            "local",
            "openai",
            "openai-responses",
            "openai-compatible",
            "anthropic-messages",
        ],
        default="local",
    )
    parser.add_argument("--llm-model", default=None)
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--output", required=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="docforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    _add_formatting_args(generate)

    format_parser = subparsers.add_parser("format")
    _add_formatting_args(format_parser)

    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("--input", required=True)
    diagnose.add_argument("--profile", default="general")

    fix = subparsers.add_parser("fix")
    fix.add_argument("--input", required=True)
    fix.add_argument("--issues", required=True)
    fix.add_argument("--output", required=True)

    args = parser.parse_args(argv)

    if args.command in {"generate", "format"}:
        try:
            profile = load_profile(args.profile)
            override = _parse_format_override(args)
            result = format_document(Path(args.input), Path(args.output), profile, override)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

        print(
            json.dumps(
                {"output": str(result.output_path), "issues": [issue.model_dump() for issue in result.issues]},
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "diagnose":
        issues = diagnose_docx(Path(args.input), load_profile(args.profile))
        print(json.dumps({"issues": [issue.model_dump() for issue in issues]}, ensure_ascii=False))
        return 0

    if args.command == "fix":
        payload = json.loads(Path(args.issues).read_text(encoding="utf-8"))
        issues = TypeAdapter(List[Issue]).validate_python(payload["issues"])
        apply_fixes(Path(args.input), Path(args.output), issues)
        print(json.dumps({"output": args.output}, ensure_ascii=False))
        return 0

    return 2


def _parse_format_override(args: argparse.Namespace):
    if not args.format_instruction:
        return None

    settings = LlmSettings(
        provider=args.llm_provider,
        api_key=args.api_key,
        model=args.llm_model,
        base_url=args.llm_base_url,
    )
    return create_llm_client(settings).parse_format_instruction(args.format_instruction)


if __name__ == "__main__":
    raise SystemExit(main())
