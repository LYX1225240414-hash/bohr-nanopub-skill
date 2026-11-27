# 字段字典（Nanopublication 断言与证据）

`output_contract` 中的字段优先：同名时以合同为准，不得改名或遗漏；本表扩展字段补充在合同字段之后。

| 字段 | 类型 | 含义 |
|---|---|---|
| case_id | string | 从 case.json 原样回填；确实没有才填 `N/A` |
| status | string | `success` / `partial` / `unable` / `refused` |
| main_result | object/array | 按题目要求的纳米出版结构；完整导出同时写入 `assertions.jsonld` |
| assertions | array | `id` / `text` / `subject` / `predicate` / `object` / `qualifiers` / `confidence` / `confidence_basis` / `evidence_ids` / `provenance_id` / `anchor` |
| evidence | array | `id` / `quote` / `anchor` / `source_type` / `relation` / `span_start` / `span_end` |
| provenance | array | `id` / `title` / `authors` / `year` / `version` / `identifier` / `source_path` / `anchor` |
| relation_vocabulary | object | 受控谓词表、判定条件与来源 |
| quality_checks | array | `check` / `target_id` / `result` / `reason` / `anchor` |
| dedup_record | array | `kept_id` / `merged_ids` / `rule` / `reason` |
| evidence_map | array | `claim` / `value` / `evidence` / `anchor` / `source_type` / `change_record` |
| verification | object | 每项 `result` + 带计数/片段的 `evidence` |
| uncertainties | array | `item` / `reason` / `anchor` / `question_for_author` |
| sources | array | 输入文件路径、页码/段号/图表号与版本 |
| change_log | array | 问题 / 修正 / 位置 / 复核结果 |

## qualifiers 允许键
`condition` / `scope` / `time` / `unit` / `negation` / `magnitude`；没有对应内容填空字符串，不编造。

## source_type 允许值
`material` / `figure` / `table` / `ocr` / `inference` / `author_confirmation`。标 `inference` 时必须同时标 `relation: indirect` 并在 `confidence_basis` 说明推理链；不得把推断写成直接证据。

## 锚点格式
`p<页>:<段>` / `p<页>:fig<号>` / `p<页>:tab<号>` / `p<页>:eq<号>` / `section:<章节>:<段>` / `ref:<编号>`。
锚点必须指向真实材料位置；无法定位的写入 uncertainties，不填伪造锚点。`evidence.quote` 必须能在该锚点找到逐字片段。

## verification 计数项
- `assertion_granularity`：单一可验证断言数 / 断言总数
- `evidence_sufficiency`：有最小充分证据的断言数 / 断言总数
- `anchor_spotcheck`：回查成功数 / 抽查数（附短引）
- `relation_direction`：方向正确的三元组数 / 检查数
- `provenance_completeness`：元数据齐全断言数 / 断言总数
- `dedup_clean`：去重后重复断言数（必须为 0）
- `no_new_facts`：材料外新增事实数（必须为 0）
- `export_parseable`：`assertions.jsonld` 可解析且字段齐全（通过项 / 检查项）
