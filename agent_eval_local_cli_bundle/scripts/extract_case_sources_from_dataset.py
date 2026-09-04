import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple


def parse_file_path(diff_text: str) -> str:
    file_path = "unknown/file.py"
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            raw = line[4:].strip()
            if raw.startswith("b/"):
                return raw[2:]
            return raw
    return file_path


def reconstruct_before_after(diff_text: str) -> Tuple[str, str]:
    before_lines: List[str] = []
    after_lines: List[str] = []

    in_hunk = False
    for line in diff_text.splitlines():
        if line.startswith("@@ "):
            in_hunk = True
            continue
        if not in_hunk:
            continue
        if line.startswith("@@ "):
            continue
        if line.startswith("\\ No newline at end of file"):
            continue

        if line.startswith("+"):
            after_lines.append(line[1:])
        elif line.startswith("-"):
            before_lines.append(line[1:])
        elif line.startswith(" "):
            content = line[1:]
            before_lines.append(content)
            after_lines.append(content)
        else:
            # For safety, treat unknown body lines as shared context.
            before_lines.append(line)
            after_lines.append(line)

    before = "\n".join(before_lines).rstrip("\n") + "\n"
    after = "\n".join(after_lines).rstrip("\n") + "\n"
    return before, after


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract benchmark case source pairs from current dataset diff patches")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json")
    parser.add_argument("--out", default="data/benchmark_case_sources.json")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    out_path = Path(args.out)

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("dataset must be a JSON array")

    sources: List[Dict] = []
    for case in data:
        diff_text = str(case.get("diff_patch", ""))
        file_path = parse_file_path(diff_text)
        before_code, after_code = reconstruct_before_after(diff_text)

        sources.append(
            {
                "case_id": case["case_id"],
                "layer": case["layer"],
                "file_path": file_path,
                "before_code": before_code,
                "after_code": after_code,
                "scene_desc": case["scene_desc"],
                "gt_review": case["gt_review"],
                "gt_key_points": case["gt_key_points"],
                "gt_forbidden_points": case["gt_forbidden_points"],
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[extract] wrote source dataset: {out_path} ({len(sources)} cases)")


if __name__ == "__main__":
    main()
