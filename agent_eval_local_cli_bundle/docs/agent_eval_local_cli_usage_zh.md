# Agent 评测系统使用说明（本地 CLI + 文件驱动）

本文档对应以下新增实现：

- data/benchmark_dataset.json
- data/benchmark_case_sources.json
- src/scheduler.py
- src/evaluator.py
- scripts/run_llm_judge_deepseek.ps1
- scripts/extract_case_sources_from_dataset.py
- scripts/rebuild_benchmark_dataset.py
- scripts/validate_benchmark_diff.py

## 1. 功能边界

- 仅本地 CLI + 文件驱动。
- 不依赖 Webhook/GitHub 回调。
- `result.json` 单文件保存每个 case 的 `meta` 与 `agent_output`。
- 支持 `--simulate` 模拟模式（内网可离线跑通骨架）。
- 保留真实 PR-Agent 调用与 LLM Judge 接入代码。

## 2. 数据集说明

文件：`data/benchmark_dataset.json`

每条 case 字段：

- `case_id`
- `layer`
- `diff_patch`
- `scene_desc`
- `gt_review`
- `gt_key_points`
- `gt_forbidden_points`

### 2.1 数据集正确性修复主线（推荐）

为彻底避免 `UnidiffParseError: Hunk is shorter than expected`，数据集改为“源样本 + 自动重建 + 强校验”模式。

- 源样本文件：`data/benchmark_case_sources.json`
- 重建脚本：`scripts/rebuild_benchmark_dataset.py`
- 校验脚本：`scripts/validate_benchmark_diff.py`

首次迁移（从旧手写 diff 提取源样本）：

```powershell
python scripts/extract_case_sources_from_dataset.py --dataset data/benchmark_dataset.json --out data/benchmark_case_sources.json
```

每次修改后建议流程：

```powershell
python scripts/rebuild_benchmark_dataset.py --source data/benchmark_case_sources.json --dataset data/benchmark_dataset.json --context 3
python scripts/validate_benchmark_diff.py --dataset data/benchmark_dataset.json
```

说明：

- `benchmark_case_sources.json` 是长期维护的“可编辑真源”。
- `benchmark_dataset.json` 是供调度器执行的“构建产物”。
- 校验脚本失败时不要继续跑调度或评测。

## 3. 调度执行（scheduler）

文件：`src/scheduler.py`

输出：

- `output/result.json`
- `output/api_summary.json`

### 3.1 模拟模式（推荐先跑）

```powershell
python src/scheduler.py --simulate --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

### 3.2 真实 PR-Agent 模式

```powershell
python src/scheduler.py --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

说明：

- 真实模式会调用 `python -m pr_agent.cli` 的 plain-diff 能力。
- 真实模型调用所需密钥（如 `OPENAI_KEY`）由你在本机环境变量提供。
- 失败 case 会计入 `api_summary.json`，并在 `result.json` 标记为 `status=failed`。

## 4. 质量评测（evaluator）

文件：`src/evaluator.py`

规则：

- 仅对 `result.json` 中 `eval_eligible=true` 的 case 评分。
- 执行失败 case 不计入质量分母。

### 4.1 GT 离线评测

```powershell
python src/evaluator.py --mode gt --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_gt.json --out-md output/eval_gt.md
```

### 4.2 LLM Judge 评测

先设置环境变量（OpenAI 兼容接口）：

```powershell
$env:OPENAI_API_KEY="<your_key>"
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
$env:OPENAI_MODEL="gpt-4o-mini"
```

执行：

```powershell
python src/evaluator.py --mode llm_judge --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_llm_judge.json --out-md output/eval_llm_judge.md
```

安全说明：

- LLM Judge 评测不会传入完整 `gt_review`。
- 仅传 `gt_key_points` 与 `gt_forbidden_points` 作为评分依据。

### 4.3 DeepSeek 一键评测脚本

文件：`scripts/run_llm_judge_deepseek.ps1`

使用示例（推荐）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_llm_judge_deepseek.ps1 -ApiKey "<your_deepseek_key>" -Model "deepseek-chat"
```

可选参数示例：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_llm_judge_deepseek.ps1 -ApiKey "<your_deepseek_key>" -Model "deepseek-reasoner" -Result "output/result.json" -Dataset "data/benchmark_dataset.json" -OutJson "output/eval_llm_judge.json" -OutMd "output/eval_llm_judge.md" -TimeoutSeconds 240
```

说明：

- 该脚本会自动设置 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`。
- 默认 DeepSeek 兼容地址为 `https://api.deepseek.com/v1`。

## 5. 你需要关注的结果文件

- `output/result.json`：每 case 单对象，包含 `meta` + `agent_output`。
- `output/api_summary.json`：接口执行汇总（含失败统计）。
- `output/eval_*.json`：评测结构化结果。
- `output/eval_*.md`：评测可读报告。

## 6. 最小回归流程

1. 先跑模拟调度。
2. 跑 GT 评测确认流程完整。
3. 在可联网机器切真实调度。
4. 最后跑 LLM Judge 评测。