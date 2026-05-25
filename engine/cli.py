from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from pydantic import TypeAdapter

from engine.converters.pandoc import convert_markdown_to_docx
from engine.diagnostics.diagnose import diagnose_docx
from engine.fixer.apply_fixes import apply_fixes
from engine.formatter.docx_formatter import apply_profile_formatting
from engine.llm.client import parse_format_instruction_locally
from engine.models import Issue
from engine.profiles.loader import load_profile


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="docforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--input", required=True)
    generate.add_argument("--profile", default="general")
    generate.add_argument("--format-instruction", default="")
    generate.add_argument("--llm-provider", choices=["local", "openai"], default="local")
    generate.add_argument("--api-key", default=None)
    generate.add_argument("--output", required=True)

    diagnose = subparsers.add_parser("diagnose")
    diagnose.add_argument("--input", required=True)
    diagnose.add_argument("--profile", default="general")

    fix = subparsers.add_parser("fix")
    fix.add_argument("--input", required=True)
    fix.add_argument("--issues", required=True)
    fix.add_argument("--output", required=True)

    args = parser.parse_args(argv)

    if args.command == "generate":
        profile = load_profile(args.profile)
        output_path = Path(args.output)
        temp_docx = output_path.with_suffix(".pandoc.docx")
        convert_markdown_to_docx(Path(args.input), temp_docx)
        override = None
        if args.format_instruction:
            if args.llm_provider == "openai":
                from engine.llm.client import OpenAIClient

                override = OpenAIClient(api_key=args.api_key).parse_format_instruction(args.format_instruction)
            else:
                override = parse_format_instruction_locally(args.format_instruction)
        apply_profile_formatting(temp_docx, output_path, profile, override)
        issues = diagnose_docx(output_path, profile)
        print(json.dumps({"output": str(output_path), "issues": [issue.model_dump() for issue in issues]}, ensure_ascii=False))
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


if __name__ == "__main__":
    raise SystemExit(main())
