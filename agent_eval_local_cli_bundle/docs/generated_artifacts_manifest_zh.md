# 本次新增文档与代码清单

## 新增文件

1. `data/benchmark_dataset.json`
2. `data/benchmark_case_sources.json`
3. `src/scheduler.py`
4. `src/evaluator.py`
5. `scripts/run_llm_judge_deepseek.ps1`
6. `scripts/extract_case_sources_from_dataset.py`
7. `scripts/rebuild_benchmark_dataset.py`
8. `scripts/validate_benchmark_diff.py`
9. `docs/agent_eval_local_cli_usage_zh.md`
10. `docs/generated_artifacts_manifest_zh.md`

## 与此前阶段文档的关系

你此前确认过的总体说明文档仍可继续参考：

- `docs/project_deep_dive_for_testing_zh.md`
- `docs/testing_docs_proposal_zh.md`

## 如何完成一次完整测试

0. 可选：重建并校验数据集（建议每次改用例后执行）

```powershell
python scripts/rebuild_benchmark_dataset.py --source data/benchmark_case_sources.json --dataset data/benchmark_dataset.json --context 3
python scripts/validate_benchmark_diff.py --dataset data/benchmark_dataset.json
```

1. 生成调度结果（simulate）：

```powershell
python src/scheduler.py --simulate --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

2. GT 评测：

```powershell
python src/evaluator.py --mode gt --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_gt.json --out-md output/eval_gt.md
```

3. 真实模式（可选）：

```powershell
python src/scheduler.py --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

4. LLM Judge（可选）：

```powershell
python src/evaluator.py --mode llm_judge --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_llm_judge.json --out-md output/eval_llm_judge.md
```

5. DeepSeek 一键脚本（可选）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_llm_judge_deepseek.ps1 -ApiKey "<your_deepseek_key>" -Model "deepseek-chat"
```

## 备注

- 执行失败 case 会进入接口统计，但不会参与质量评分。
- `result.json` 单文件包含 `meta` 与 `agent_output`，未做物理拆分。