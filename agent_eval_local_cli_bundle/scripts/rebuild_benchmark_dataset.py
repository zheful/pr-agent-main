import argparse
import difflib
import json
from pathlib import Path
from typing import Dict, List

from unidiff import PatchSet


def build_unified_diff(file_path: str, before_code: str, after_code: str, context_lines: int = 3) -> str:
    before_lines = before_code.splitlines(keepends=True)
    after_lines = after_code.splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=context_lines,
            lineterm="\n",
        )
    )
    diff_text = "".join(diff_lines)
    if not diff_text.endswith("\n"):
        diff_text += "\n"
    return diff_text


def validate_diff(diff_text: str) -> None:
    PatchSet(diff_text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild benchmark dataset with valid unified diff patches")
    parser.add_argument("--source", default="data/benchmark_case_sources.json")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json")
    parser.add_argument("--context", type=int, default=3)
    args = parser.parse_args()

    source_path = Path(args.source)
    dataset_path = Path(args.dataset)

    sources = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(sources, list):
        raise ValueError("source must be a JSON array")

    out: List[Dict] = []
    for item in sources:
        file_path = str(item.get("file_path", "unknown/file.py"))
        before_code = str(item.get("before_code", ""))
        after_code = str(item.get("after_code", ""))

        diff_patch = build_unified_diff(file_path, before_code, after_code, context_lines=args.context)
        validate_diff(diff_patch)

        out.append(
            {
                "case_id": item["case_id"],
                "layer": item["layer"],
                "diff_patch": diff_patch,
                "scene_desc": item["scene_desc"],
                "gt_review": item["gt_review"],
                "gt_key_points": item["gt_key_points"],
                "gt_forbidden_points": item["gt_forbidden_points"],
            }
        )

    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    dataset_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[rebuild] wrote dataset: {dataset_path} ({len(out)} cases)")


if __name__ == "__main__":
    main()
