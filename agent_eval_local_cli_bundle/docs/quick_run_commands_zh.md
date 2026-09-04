# 一次跑完三段测试的命令清单（可直接复制）

## 0. 进入项目目录

```powershell
cd <你的项目目录>
```

## 1. 创建并激活虚拟环境（首次）

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r requirements.txt
```

## 2. 接口测试（simulate，本地可离线）

```powershell
python src/scheduler.py --simulate --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

## 3. 质量测试（GT）

```powershell
python src/evaluator.py --mode gt --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_gt.json --out-md output/eval_gt.md
```

## 4. 质量测试（DeepSeek，大模型）

### 4.1 一键脚本方式（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_llm_judge_deepseek.ps1 -ApiKey "<your_deepseek_key>" -Model "deepseek-chat"
```

### 4.2 手动环境变量方式

```powershell
$env:OPENAI_API_KEY="<your_deepseek_key>"
$env:OPENAI_BASE_URL="https://api.deepseek.com/v1"
$env:OPENAI_MODEL="deepseek-chat"
$env:EVAL_JUDGE_TIMEOUT_SECONDS="180"
python src/evaluator.py --mode llm_judge --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_llm_judge.json --out-md output/eval_llm_judge.md
```

## 5. 查看结果文件

```powershell
Get-Content output/api_summary.json
Get-Content output/eval_gt.json
Get-Content output/eval_llm_judge.json
```

```powershell
Get-Content output/eval_gt.md
Get-Content output/eval_llm_judge.md
```

## 6. 可选：真实 PR-Agent 调度（非 simulate）

```powershell
python src/scheduler.py --dataset data/benchmark_dataset.json --result output/result.json --api-summary output/api_summary.json
```

## 7. 失败排查最短命令

```powershell
python src/evaluator.py --mode llm_judge --result output/result.json --dataset data/benchmark_dataset.json --out-json output/eval_llm_judge.json --out-md output/eval_llm_judge.md
```

```powershell
Get-Content output/eval_llm_judge.json
```

说明：

- `judge_failed_cases` 大于 0 时，优先看每个 case 的 `judge_error`。
- 若超时，增大 `EVAL_JUDGE_TIMEOUT_SECONDS`。