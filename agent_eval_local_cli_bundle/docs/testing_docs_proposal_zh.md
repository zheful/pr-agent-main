# 测试文档方案评审（仅方案，不实施）

## 1. 你当前设想的合理性评估

你给出的四项设想整体方向正确，且与 PR-Agent 架构匹配：

1. Benchmark 数据集（用例 + GT）
2. 自动化接口测试脚本
3. 执行输出（接口结果、质量评测输入）物理分离
4. 质量评测脚本（GT 对比 + 外接 LLM Judge）

结论：合理，可执行。

但从工程落地角度还缺 3 个关键件：

1. 评测规范文档：定义指标口径、阈值、统计方式。
2. 运行配置文档：定义模型、温度、token、重试、并发等实验变量。
3. 结果解读文档：定义通过/告警/失败判定与回归策略。

## 2. 建议的文档全集（先文档，后实现）

建议在 docs/testing/ 下维护以下文档。

## 2.1 00_testing_scope.md

作用：定义测试边界与目标。

应包含：

- 测试对象：调度层接口、质量评测。
- 非目标：暂不覆盖的能力。
- 环境约束：Python 版本、依赖、凭证策略。
- 成功标准：最小可用标准。

## 2.2 01_benchmark_dataset_spec.md

作用：规范 Benchmark 数据结构与字段。

应包含：

- case 文件 schema（输入 diff、命令、上下文）。
- gt 文件 schema（期望标签、期望要点、禁止项）。
- 数据分层：smoke/core/hard。
- 数据版本化与变更规则。

## 2.3 02_dispatch_interface_test_spec.md

作用：定义调度层接口测试点。

应包含：

- CLI 入口测试矩阵。
- Webhook 事件矩阵（PR opened/comment/sync 等）。
- 配置优先级测试矩阵。
- 异常与安全测试矩阵（签名失败、非法参数、缺 token）。

## 2.4 03_execution_artifact_spec.md

作用：统一输出产物与目录结构。

应包含：

- 接口结果文件规范。
- 质量评测输入文件规范。
- 元数据字段：run_id、case_id、model、config_hash、input_hash。
- 失败重试与状态码约定。

## 2.5 04_quality_eval_gt_spec.md

作用：定义 GT 对比评分。

应包含：

- 指标：结构合规、关键信息覆盖、误报率、漏报率。
- 文本匹配策略：关键词+语义混合。
- 聚合方式：按 case、按能力、总体。
- 阈值策略：通过线、告警线。

## 2.6 05_quality_eval_llm_judge_spec.md

作用：定义外接 LLM-as-judge 评测。

应包含：

- Judge Prompt 模板与评分 rubric。
- 控偏策略：双评审/多次采样/一致性检查。
- 防泄漏规则：禁止将 GT 直接暴露给 judge。
- 成本统计：token、调用时延、失败率。

## 2.7 06_reporting_spec.md

作用：定义最终报告格式。

应包含：

- 明细报告（每 case）。
- 聚合报告（能力维度/模型维度）。
- 趋势报告（版本对比）。
- 回归判定与 release gate。

## 2.8 07_runbook.md

作用：定义执行与排障流程。

应包含：

- 一键执行步骤。
- 常见失败场景与处理。
- 环境差异检查项。
- 结果复现实操步骤。

## 3. 你原始四项与建议文档映射关系

- 你的 1（Benchmark 数据集）对应：01。
- 你的 2（接口测试脚本）对应：02 + 07。
- 你的 3（执行输出分离）对应：03。
- 你的 4A（GT 模式）对应：04。
- 你的 4B（LLM Judge）对应：05。
- 你要求的详细指标报告对应：06。

## 4. 建议的目录草案

docs/testing/

- 00_testing_scope.md
- 01_benchmark_dataset_spec.md
- 02_dispatch_interface_test_spec.md
- 03_execution_artifact_spec.md
- 04_quality_eval_gt_spec.md
- 05_quality_eval_llm_judge_spec.md
- 06_reporting_spec.md
- 07_runbook.md

## 5. 先行约束（避免后续返工）

1. 所有评测必须记录完整配置快照，否则结果不可复现。
2. 先固定一套基线模型与温度，再扩展多模型横评。
3. 先跑 deterministic 子集（plain-diff + 小样本）再扩展全量。
4. LLM Judge 结论必须可追溯到评分维度与解释文本。

## 6. 下一步（仍是文档阶段）

建议下一步先把 01、03、04、05 四个文档定稿，因为它们是后续脚本实现的接口契约。

---

本文件仅提供测试文档方案评审，不包含脚本开发、执行部署或环境改造。