import argparse
import json
from collections import Counter
from pathlib import Path

from unidiff import PatchSet


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate benchmark unified diff patches")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("dataset must be a JSON array")

    errors = []
    ids = set()
    layer_counter = Counter()

    for case in data:
        case_id = case.get("case_id")
        layer = case.get("layer")
        layer_counter[layer] += 1

        if case_id in ids:
            errors.append((case_id, "duplicate_case_id"))
        ids.add(case_id)

        for key in ["case_id", "layer", "diff_patch", "scene_desc", "gt_review", "gt_key_points", "gt_forbidden_points"]:
            if key not in case:
                errors.append((case_id, f"missing_field:{key}"))

        try:
            patch = PatchSet(str(case.get("diff_patch", "")))
            if len(patch) == 0:
                errors.append((case_id, "empty_patch"))
            else:
                for pf in patch:
                    if len(pf) == 0:
                        errors.append((case_id, "patch_has_no_hunks"))
        except Exception as e:
            errors.append((case_id, f"parse_error:{e}"))

    print(f"[validate] total_cases={len(data)} layers={dict(layer_counter)}")

    if errors:
        print(f"[validate] failed_cases={len(errors)}")
        for cid, err in errors:
            print(f"- {cid}: {err}")
        raise SystemExit(1)

    print("[validate] all diff patches are valid")


if __name__ == "__main__":
    main()
