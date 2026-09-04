# 36 条分层 Case 覆盖点矩阵

本矩阵用于说明 `data/benchmark_dataset.json` 中 36 条用例的覆盖范围。

- 分层规模：S=10, C=18, H=8
- 主要覆盖维度：
  - correctness（正确性）
  - security（安全）
  - robustness（健壮性）
  - maintainability（可维护性）
  - testing_guidance（测试建议）
  - noise_control（误报控制）
  - large_diff（大变更上下文）
  - observability（可观测性）
  - contract_change（接口契约变更）
  - idempotency（幂等性）

## Smoke（S001-S010）

| case_id | layer | primary_focus | secondary_focus |
|---|---|---|---|
| S001 | smoke | correctness | robustness |
| S002 | smoke | security | maintainability |
| S003 | smoke | robustness | contract_change |
| S004 | smoke | correctness | testing_guidance |
| S005 | smoke | robustness | correctness |
| S006 | smoke | contract_change | robustness |
| S007 | smoke | correctness | testing_guidance |
| S008 | smoke | robustness | observability |
| S009 | smoke | robustness | noise_control |
| S010 | smoke | security | observability |

## Core（C001-C018）

| case_id | layer | primary_focus | secondary_focus |
|---|---|---|---|
| C001 | core | security | observability |
| C002 | core | idempotency | robustness |
| C003 | core | security | correctness |
| C004 | core | correctness | idempotency |
| C005 | core | security | correctness |
| C006 | core | correctness | robustness |
| C007 | core | security | maintainability |
| C008 | core | security | observability |
| C009 | core | security | correctness |
| C010 | core | idempotency | robustness |
| C011 | core | robustness | correctness |
| C012 | core | contract_change | testing_guidance |
| C013 | core | security | observability |
| C014 | core | idempotency | robustness |
| C015 | core | robustness | maintainability |
| C016 | core | correctness | robustness |
| C017 | core | observability | robustness |
| C018 | core | correctness | testing_guidance |

## Hard（H001-H008）

| case_id | layer | primary_focus | secondary_focus |
|---|---|---|---|
| H001 | hard | large_diff | observability |
| H002 | hard | correctness | contract_change |
| H003 | hard | security | correctness |
| H004 | hard | robustness | observability |
| H005 | hard | contract_change | robustness |
| H006 | hard | security | robustness |
| H007 | hard | observability | maintainability |
| H008 | hard | idempotency | observability |

## 维度覆盖汇总（按主覆盖）

- correctness: 10
- security: 10
- robustness: 8
- idempotency: 4
- contract_change: 3
- observability: 2
- large_diff: 1

说明：

- 主覆盖用于报告分桶和回归基线分析。
- 次覆盖用于辅助解释 case 评分波动。
- 该矩阵与数据集解耦，不影响现有 `scheduler.py` / `evaluator.py` 的运行逻辑。