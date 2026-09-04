import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _contains_phrase(text: str, phrase: str) -> bool:
    return _normalize_text(phrase) in _normalize_text(text)


def _gt_score(agent_text: str, key_points: List[str], forbidden_points: List[str]) -> Dict[str, Any]:
    key_points = key_points or []
    forbidden_points = forbidden_points or []

    key_hits = [p for p in key_points if _contains_phrase(agent_text, p)]
    forbidden_hits = [p for p in forbidden_points if _contains_phrase(agent_text, p)]

    coverage = (len(key_hits) / len(key_points)) if key_points else 1.0
    violation_rate = (len(forbidden_hits) / len(forbidden_points)) if forbidden_points else 0.0
    format_pass = 1.0 if agent_text.strip() else 0.0

    overall = (0.7 * coverage) + (0.2 * format_pass) + (0.1 * (1.0 - violation_rate))

    return {
        "coverage": round(coverage, 4),
        "violation_rate": round(violation_rate, 4),
        "format_pass": format_pass,
        "key_points_hit": key_hits,
        "forbidden_points_hit": forbidden_hits,
        "score": round(overall * 100, 2),
    }


def _resolve_judge_url(base_url: str) -> str:
    base = (base_url or "").strip().rstrip("/")
    if not base:
        base = "https://api.openai.com/v1"
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _extract_json_object(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("Judge response is not valid JSON")
    return json.loads(match.group(0))


def _call_llm_judge(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
    scene_desc: str,
    diff_patch: str,
    agent_output: str,
    gt_key_points: List[str],
    gt_forbidden_points: List[str],
) -> Dict[str, Any]:
    """
    SECURITY CONSTRAINT:
    Do NOT pass full gt_review to judge. Only pass key points and forbidden points.
    """
    judge_url = _resolve_judge_url(base_url)

    clipped_diff = diff_patch[:8000]
    clipped_output = agent_output[:12000]

    system_prompt = (
        "You are a strict PR review evaluator. "
        "Return JSON only with keys: score_0_10, key_points_hit, forbidden_triggered, reasoning."
    )

    # Note: no full gt_review field in user_prompt.
    user_payload = {
        "scene_desc": scene_desc,
        "diff_patch": clipped_diff,
        "agent_output": clipped_output,
        "gt_key_points": gt_key_points,
        "gt_forbidden_points": gt_forbidden_points,
        "rubric": {
            "score_0_10": "10 is excellent, 0 is unusable.",
            "key_points_hit": "List only key points explicitly covered by agent output.",
            "forbidden_triggered": "List forbidden points triggered by agent output.",
            "reasoning": "Brief explanation with concrete evidence.",
        },
    }

    request_body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }

    req = urllib.request.Request(
        judge_url,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        raise RuntimeError(f"judge_http_error status={e.code} body={body[:1000]}") from e
    except Exception as e:
        raise RuntimeError(f"judge_request_failed: {e}") from e

    response_json = json.loads(raw)
    content = response_json["choices"][0]["message"]["content"]
    parsed = _extract_json_object(content)

    score = float(parsed.get("score_0_10", 0.0))
    key_hits = parsed.get("key_points_hit", []) or []
    forbidden_hits = parsed.get("forbidden_triggered", []) or []

    return {
        "score_0_10": round(score, 3),
        "key_points_hit": key_hits,
        "forbidden_triggered": forbidden_hits,
        "reasoning": parsed.get("reasoning", ""),
    }


def _aggregate(scores: List[float]) -> float:
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 3)


def _write_markdown_report(path: Path, report: Dict[str, Any], mode: str) -> None:
    lines = []
    lines.append(f"# Evaluator Report ({mode})")
    lines.append("")
    summary = report.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total_result_cases: {summary.get('total_result_cases', 0)}")
    lines.append(f"- execution_failed_cases: {summary.get('execution_failed_cases', 0)}")
    lines.append(f"- quality_eligible_cases: {summary.get('quality_eligible_cases', 0)}")
    lines.append(f"- scored_cases: {summary.get('scored_cases', 0)}")

    if mode == "gt":
        lines.append(f"- average_score_100: {summary.get('average_score_100', 0)}")
        lines.append(f"- average_coverage: {summary.get('average_coverage', 0)}")
        lines.append(f"- average_violation_rate: {summary.get('average_violation_rate', 0)}")
    else:
        lines.append(f"- average_score_0_10: {summary.get('average_score_0_10', 0)}")
        lines.append(f"- judge_failed_cases: {summary.get('judge_failed_cases', 0)}")

    lines.append("")
    lines.append("## Per Case")
    lines.append("")

    for row in report.get("cases", []):
        lines.append(f"### {row.get('case_id')}")
        lines.append(f"- layer: {row.get('layer')}")
        lines.append(f"- status: {row.get('status')}")
        if mode == "gt":
            lines.append(f"- score_100: {row.get('score_100')}")
            lines.append(f"- coverage: {row.get('coverage')}")
            lines.append(f"- violation_rate: {row.get('violation_rate')}")
        else:
            lines.append(f"- score_0_10: {row.get('score_0_10')}")
            if row.get("judge_error"):
                lines.append(f"- judge_error: {row.get('judge_error')}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def evaluate_gt(results: List[Dict[str, Any]], dataset_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    rows = []
    scores = []
    coverages = []
    violations = []

    execution_failed = 0
    eligible = 0

    for item in results:
        meta = item.get("meta", {})
        case_id = meta.get("case_id")
        layer = meta.get("layer")
        status = meta.get("status")

        if status != "success" or not item.get("eval_eligible", False):
            execution_failed += 1
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "execution_failed",
                "score_100": None,
                "coverage": None,
                "violation_rate": None,
            })
            continue

        eligible += 1
        ds = dataset_map.get(case_id)
        if not ds:
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "missing_dataset_case",
                "score_100": None,
                "coverage": None,
                "violation_rate": None,
            })
            continue

        agent_text = item.get("agent_output", {}).get("raw_text", "")
        scored = _gt_score(agent_text, ds.get("gt_key_points", []), ds.get("gt_forbidden_points", []))

        rows.append({
            "case_id": case_id,
            "layer": layer,
            "status": "scored",
            "score_100": scored["score"],
            "coverage": scored["coverage"],
            "violation_rate": scored["violation_rate"],
            "key_points_hit": scored["key_points_hit"],
            "forbidden_points_hit": scored["forbidden_points_hit"],
        })

        scores.append(scored["score"])
        coverages.append(scored["coverage"])
        violations.append(scored["violation_rate"])

    summary = {
        "total_result_cases": len(results),
        "execution_failed_cases": execution_failed,
        "quality_eligible_cases": eligible,
        "scored_cases": len(scores),
        "average_score_100": _aggregate(scores),
        "average_coverage": _aggregate(coverages),
        "average_violation_rate": _aggregate(violations),
    }

    return {"mode": "gt", "summary": summary, "cases": rows}


def evaluate_llm_judge(
    results: List[Dict[str, Any]],
    dataset_map: Dict[str, Dict[str, Any]],
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
) -> Dict[str, Any]:
    rows = []
    execution_failed = 0
    eligible = 0
    judge_failed = 0
    scores = []

    for item in results:
        meta = item.get("meta", {})
        case_id = meta.get("case_id")
        layer = meta.get("layer")
        status = meta.get("status")

        if status != "success" or not item.get("eval_eligible", False):
            execution_failed += 1
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "execution_failed",
                "score_0_10": None,
            })
            continue

        eligible += 1
        ds = dataset_map.get(case_id)
        if not ds:
            judge_failed += 1
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "missing_dataset_case",
                "score_0_10": None,
                "judge_error": "dataset case not found",
            })
            continue

        agent_text = item.get("agent_output", {}).get("raw_text", "")

        try:
            judged = _call_llm_judge(
                base_url=base_url,
                api_key=api_key,
                model=model,
                timeout=timeout,
                scene_desc=str(ds.get("scene_desc", "")),
                diff_patch=str(ds.get("diff_patch", "")),
                agent_output=agent_text,
                gt_key_points=ds.get("gt_key_points", []),
                gt_forbidden_points=ds.get("gt_forbidden_points", []),
            )
            score = float(judged["score_0_10"])
            scores.append(score)
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "scored",
                "score_0_10": round(score, 3),
                "key_points_hit": judged.get("key_points_hit", []),
                "forbidden_triggered": judged.get("forbidden_triggered", []),
                "reasoning": judged.get("reasoning", ""),
            })
        except Exception as e:
            judge_failed += 1
            rows.append({
                "case_id": case_id,
                "layer": layer,
                "status": "judge_failed",
                "score_0_10": None,
                "judge_error": str(e),
            })

    summary = {
        "total_result_cases": len(results),
        "execution_failed_cases": execution_failed,
        "quality_eligible_cases": eligible,
        "scored_cases": len(scores),
        "judge_failed_cases": judge_failed,
        "average_score_0_10": _aggregate(scores),
    }

    return {"mode": "llm_judge", "summary": summary, "cases": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality evaluator for local agent evaluation results")
    parser.add_argument("--mode", choices=["gt", "llm_judge"], required=True, help="Evaluation mode")
    parser.add_argument("--result", default="output/result.json", help="Path to scheduler result json")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json", help="Path to benchmark dataset")
    parser.add_argument("--out-json", default="output/eval_report.json", help="Path to output JSON report")
    parser.add_argument("--out-md", default="output/eval_report.md", help="Path to output Markdown report")
    parser.add_argument("--judge-base-url", default=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    parser.add_argument("--judge-model", default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    parser.add_argument("--judge-timeout", type=int, default=int(os.environ.get("EVAL_JUDGE_TIMEOUT_SECONDS", "120")))
    args = parser.parse_args()

    result_path = Path(args.result)
    dataset_path = Path(args.dataset)
    out_json_path = Path(args.out_json)
    out_md_path = Path(args.out_md)

    results = _load_json(result_path)
    dataset = _load_json(dataset_path)

    if not isinstance(results, list):
        raise ValueError("result.json must be a JSON array")
    if not isinstance(dataset, list):
        raise ValueError("benchmark_dataset.json must be a JSON array")

    dataset_map = {str(item.get("case_id")): item for item in dataset}

    if args.mode == "gt":
        report = evaluate_gt(results, dataset_map)
    else:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for --mode llm_judge")
        report = evaluate_llm_judge(
            results=results,
            dataset_map=dataset_map,
            base_url=args.judge_base_url,
            api_key=api_key,
            model=args.judge_model,
            timeout=args.judge_timeout,
        )

    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    with out_json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    _write_markdown_report(out_md_path, report, args.mode)

    print(f"[evaluator] mode={args.mode}")
    print(f"[evaluator] wrote json report: {out_json_path}")
    print(f"[evaluator] wrote markdown report: {out_md_path}")


if __name__ == "__main__":
    main()
