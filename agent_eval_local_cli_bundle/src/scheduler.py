import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_dataset(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("benchmark_dataset.json must be a JSON array")
    required = {
        "case_id",
        "layer",
        "diff_patch",
        "scene_desc",
        "gt_review",
        "gt_key_points",
        "gt_forbidden_points",
    }
    for idx, case in enumerate(data):
        missing = sorted(required.difference(case.keys()))
        if missing:
            raise ValueError(f"case index {idx} missing fields: {missing}")
    return data


def _simulate_agent_output(case: Dict[str, Any]) -> str:
    diff = str(case.get("diff_patch", ""))
    lowered = diff.lower()

    findings = []
    if "eval(" in lowered or "exec(" in lowered:
        findings.append("发现高风险动态执行调用（eval/exec），建议立即替换为安全解析或白名单机制。")
    if "token" in lowered and "logger" in lowered:
        findings.append("疑似敏感信息被写入日志，建议对 token 等字段做脱敏或移除。")
    if "select *" in lowered and "%" in lowered:
        findings.append("疑似 SQL 拼接，建议使用参数化查询防止注入。")
    if "return {'error'" in lowered or "return {\"error\"" in lowered:
        findings.append("新增了显式错误返回，建议统一错误码和错误响应结构。")
    if "timeout" in lowered and "retry" in lowered:
        findings.append("出现超时重试路径，建议确认幂等性，避免重复副作用。")
    if "send_file('/tmp/'" in lowered or "send_file(\"/tmp/" in lowered:
        findings.append("存在用户输入参与文件路径拼接的风险，建议做路径规范化和白名单控制。")

    if not findings:
        findings.append("未发现明确高危问题，建议补充边界测试并确认改动与业务意图一致。")

    bullets = "\n".join(f"- {item}" for item in findings)
    return (
        "## PR Review (Simulated)\n\n"
        f"### Case\n- case_id: {case.get('case_id')}\n- layer: {case.get('layer')}\n\n"
        "### Findings\n"
        f"{bullets}\n\n"
        "### Suggested Follow-ups\n"
        "- 增加对应单元测试和异常路径测试。\n"
        "- 对高风险路径补充日志审计与告警规则。\n"
    )


def _invoke_real_pr_agent(case: Dict[str, Any], timeout: int) -> Dict[str, Any]:
    """
    REAL INTEGRATION POINT:
    This function calls PR-Agent CLI in plain-diff mode.
    If you need custom model/provider switching, modify command/env here.
    """
    with tempfile.TemporaryDirectory(prefix="agent_eval_") as td:
        td_path = Path(td)
        diff_path = td_path / "input.diff"
        output_path = td_path / "agent_output.md"

        diff_path.write_text(str(case.get("diff_patch", "")), encoding="utf-8")

        command = [
            sys.executable,
            "-m",
            "pr_agent.cli",
            "--diff-file",
            str(diff_path),
            "--output",
            str(output_path),
            "review",
        ]

        env = os.environ.copy()

        start = time.perf_counter()
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""

        raw_text = ""
        if output_path.exists():
            raw_text = output_path.read_text(encoding="utf-8", errors="replace")
        if not raw_text.strip():
            raw_text = stdout.strip()

        if completed.returncode != 0:
            err_msg = stderr.strip() or stdout.strip() or "pr_agent cli exited non-zero"
            return {
                "ok": False,
                "raw_text": raw_text,
                "error_type": "pr_agent_non_zero_exit",
                "error_message": err_msg[:2000],
                "latency_ms": elapsed_ms,
                "command": command,
            }

        if not raw_text.strip():
            return {
                "ok": False,
                "raw_text": "",
                "error_type": "empty_agent_output",
                "error_message": "PR-Agent finished but produced empty output",
                "latency_ms": elapsed_ms,
                "command": command,
            }

        return {
            "ok": True,
            "raw_text": raw_text,
            "error_type": "",
            "error_message": "",
            "latency_ms": elapsed_ms,
            "command": command,
        }


def _run_case(case: Dict[str, Any], run_id: str, simulate: bool, timeout: int) -> Dict[str, Any]:
    start_ts = _now_iso()
    start = time.perf_counter()

    try:
        if simulate:
            raw_text = _simulate_agent_output(case)
            latency_ms = int((time.perf_counter() - start) * 1000)
            status = "success"
            error_type = ""
            error_message = ""
            pr_agent_cmd = ["SIMULATED"]
        else:
            result = _invoke_real_pr_agent(case, timeout=timeout)
            raw_text = result["raw_text"]
            latency_ms = int(result["latency_ms"])
            status = "success" if result["ok"] else "failed"
            error_type = result["error_type"]
            error_message = result["error_message"]
            pr_agent_cmd = result["command"]
    except subprocess.TimeoutExpired as e:
        raw_text = ""
        latency_ms = int((time.perf_counter() - start) * 1000)
        status = "failed"
        error_type = "timeout"
        error_message = str(e)
        pr_agent_cmd = ["TIMEOUT"]
    except Exception as e:
        raw_text = ""
        latency_ms = int((time.perf_counter() - start) * 1000)
        status = "failed"
        error_type = "runtime_error"
        error_message = str(e)
        pr_agent_cmd = ["RUNTIME_ERROR"]

    end_ts = _now_iso()
    eval_eligible = status == "success"

    return {
        "meta": {
            "run_id": run_id,
            "case_id": case.get("case_id"),
            "layer": case.get("layer"),
            "mode": "simulate" if simulate else "real",
            "status": status,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "latency_ms": latency_ms,
            "error_type": error_type,
            "error_message": error_message,
            "pr_agent_cmd": pr_agent_cmd,
        },
        "agent_output": {
            "raw_text": raw_text,
            "normalized": {
                "char_count": len(raw_text),
                "line_count": len(raw_text.splitlines()) if raw_text else 0,
            },
        },
        "eval_eligible": eval_eligible,
    }


def _build_api_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    success = 0
    failed = 0
    latency_values = []
    failure_breakdown: Dict[str, int] = {}

    for item in results:
        meta = item.get("meta", {})
        status = meta.get("status")
        latency = int(meta.get("latency_ms", 0) or 0)
        latency_values.append(latency)

        if status == "success":
            success += 1
        else:
            failed += 1
            et = meta.get("error_type") or "unknown_error"
            failure_breakdown[et] = failure_breakdown.get(et, 0) + 1

    avg_latency = int(sum(latency_values) / total) if total else 0
    success_rate = round((success / total) * 100, 2) if total else 0.0

    return {
        "total_cases": total,
        "success_cases": success,
        "failed_cases": failed,
        "success_rate": success_rate,
        "avg_latency_ms": avg_latency,
        "failure_breakdown": failure_breakdown,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch scheduler for local CLI + file-driven PR-Agent evaluation")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json", help="Path to benchmark dataset json")
    parser.add_argument("--result", default="output/result.json", help="Path to output result json")
    parser.add_argument("--api-summary", default="output/api_summary.json", help="Path to API summary json")
    parser.add_argument("--simulate", action="store_true", help="Enable simulate mode (no real PR-Agent model call)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout seconds per case in real mode")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    result_path = Path(args.result)
    api_summary_path = Path(args.api_summary)

    dataset = _load_dataset(dataset_path)

    run_id = str(uuid.uuid4())
    results = []
    for case in dataset:
        results.append(_run_case(case=case, run_id=run_id, simulate=args.simulate, timeout=args.timeout))

    api_summary = _build_api_summary(results)

    result_path.parent.mkdir(parents=True, exist_ok=True)
    api_summary_path.parent.mkdir(parents=True, exist_ok=True)

    with result_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    with api_summary_path.open("w", encoding="utf-8") as f:
        json.dump(api_summary, f, ensure_ascii=False, indent=2)

    print(f"[scheduler] run_id={run_id}")
    print(f"[scheduler] mode={'simulate' if args.simulate else 'real'}")
    print(f"[scheduler] wrote result: {result_path}")
    print(f"[scheduler] wrote api summary: {api_summary_path}")


if __name__ == "__main__":
    main()
