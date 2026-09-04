# 拷贝包位置与内容说明

## 1. 拷贝包根目录

`delivery_bundle/agent_eval_local_cli_bundle`

你可以直接复制整个目录到其他机器运行。

## 2. 目录内容

- `data/benchmark_dataset.json`：基准数据集（含样例）。
- `data/benchmark_case_sources.json`：基准源样本（before/after 真源）。
- `src/scheduler.py`：批量调度脚本，支持 `--simulate` 与真实 PR-Agent 调用。
- `src/evaluator.py`：质量评测脚本，支持 `--mode gt` 与 `--mode llm_judge`。
- `scripts/run_llm_judge_deepseek.ps1`：DeepSeek 一键质量评测脚本。
- `scripts/extract_case_sources_from_dataset.py`：从旧数据集提取源样本。
- `scripts/rebuild_benchmark_dataset.py`：从源样本重建合法 unified diff 数据集。
- `scripts/validate_benchmark_diff.py`：逐条校验 diff 可解析性。
- `docs/agent_eval_local_cli_usage_zh.md`：完整使用说明。
- `docs/generated_artifacts_manifest_zh.md`：新增文件清单与最小测试流程。
- `docs/project_deep_dive_for_testing_zh.md`：项目深度说明。
- `docs/testing_docs_proposal_zh.md`：测试方案文档。
- `docs/benchmark_coverage_matrix_zh.md`：36 条用例覆盖点矩阵。
- `output/result.json`：simulate 调度产物（已跑通）。
- `output/api_summary.json`：simulate 接口统计（已跑通）。
- `output/eval_gt.json`：GT 评测 JSON 报告（已跑通）。
- `output/eval_gt.md`：GT 评测 Markdown 报告（已跑通）。

## 3. 在新机器上的最小执行步骤

1. 进入目录：

```powershell
cd agent_eval_local_cli_bundle
```

2. 先跑模拟调度：

```powershell
python src/scheduler.py --simulate --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

3. 跑 GT 评测：

```powershell
python src/evaluator.py --mode gt --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_gt.json --out-md output/eval_gt.md
```

4. 真实模式与 LLM Judge 见：`docs/agent_eval_local_cli_usage_zh.md`。

5. DeepSeek 一键评测（可选）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_llm_judge_deepseek.ps1 -ApiKey "<your_deepseek_key>" -Model "deepseek-chat"
```

6. 数据集重建与校验（建议每次改 case 后执行）：

```powershell
python scripts/rebuild_benchmark_dataset.py --source data/benchmark_case_sources.json --dataset data/benchmark_dataset.json --context 3
python scripts/validate_benchmark_diff.py --dataset data/benchmark_dataset.json
```
