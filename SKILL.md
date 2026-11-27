---
name: nanopub-assertion-builder
description: "面向 Nanopublication 的科研断言拆分与证据绑定 Agent Skill：从真实论文材料拆出单一可判断真假的断言，受控关系映射为主体-谓词-客体三元组，为每条断言绑定最小充分证据片段与页码段落锚点，补齐作者年份版本等来源元数据，执行粒度、证据充分性、去重与方向校验并输出带计数自检的 result.json；当用户要求构建纳米出版、抽取结构化科研结论、核验断言与证据时使用，支持中英文论文与跨图表证据。"
---

# Nanopublication：拆得细、对得上、追得回、读得懂

把论文段落变成**可机器读取、可逐条回原文复核**的断言-证据-来源结构，而不是把整段摘要塞进一个字段。本 Skill 锁定题面四项要求：**拆得细**（每条断言单一、可判断真假，保留条件与限定范围）、**对得上**（最小充分证据片段与断言一一绑定）、**追得回**（断言、证据、论文、作者、年份、版本链路完整）、**读得懂**（字段与序列化形态可被下游直接解析）。

## 何时使用

- 从真实论文中抽取关键结论，拆成单一可验证断言并绑定证据与来源。
- 需要受控关系词表、主体/客体区分、置信度依据、去重合并与质量检查。
- 需要证明加载 Skill 后相对基础 Agent 在断言粒度、证据质量与可复用性上的增益。

不适用：无原文材料、要求整段摘要原样充当断言、要求编造来源或评测成绩的场景。

## 运行环境与输出路径（重要）

- 平台把本 Skill 安装到 `/skills/weekly-skill`，用固定的 3 个案例运行。先读真实输入 `/input/case.json` 与 `/input/task.md`；`case.json` 可能含 `case_id`、`output_contract`、论文/材料路径、目标字段与约束。**以实际字段为准，不从题目标签、文件名或示例推断材料内容**。
- 中间文件（段落切分表、候选断言、证据片段、校验记录）写在 `/app/work`，不污染输入目录；资源从 `/skills/weekly-skill/resources/` 读取，均为 UTF-8 文本。
- 最终结构化结果写到 `/app/output/result.json`（UTF-8 合法 JSON），**完整原样回填 `output_contract` 的全部字段与 `case_id`**，再补充本 Skill 的扩展字段；合同字段与本表同名时以合同为准。
- 同时写出 `/app/output/assertions.jsonld`（或合同指定的结构化导出路径，采用 JSON-LD 风格并含上下文说明）、`/app/output/evidence_map.md`（逐条断言 → 原文短引 → 锚点）、`/app/output/provenance.md`（论文、作者、年份、版本、标识符）、`/app/output/quality_report.md`（粒度、方向、去重、证据充分性检查记录）。若 `output_contract` 指定其他产物路径，以合同为准。
- 预算内**尽早写入诚实的部分结果**再增量完善：64 次模型请求、900 秒、单次 16384 tokens；3 个案例由平台安排，参赛者不提供测试案例、白板或正式答案。
- 让可核验操作轨迹覆盖逐段打开、候选断言生成、证据回查、词表映射、去重、校验与回修等 **≥30 个真实动作**，不要只抛出一个最终结论；不得为凑数编造命令或日志。
- 禁止提交预制答案、正式案例答案或假造的证据与来源；本 Skill 包内不应含任何 `result.json`。
- 资源限制：最多 50 个 UTF-8 文本文件、单文件 ≤500KB、总计 ≤2MB、无符号链接。

## 输入输出

输入：论文全文或段落、图表说明与元数据，以及任务说明；可选约束：关系词表、目标字段、断言数量或粒度要求。

输出 `result.json` 字段如下（`output_contract` 优先）：

| 字段 | 要求 |
|---|---|
| case_id | 从 case.json 原样回填；确实没有才填 `N/A` |
| status | `success` / `partial` / `unable` / `refused`；部分完成写明未处理段落与人工接管位置 |
| main_result | 按题目要求的纳米出版结构：断言数组、证据与来源引用；完整导出同时写入 `assertions.jsonld` |
| assertions | 数组，每项 `id` / `text` / `subject` / `predicate` / `object` / `qualifiers`（条件、范围、否定、单位）/ `confidence` / `confidence_basis` / `evidence_ids` / `provenance_id` / `anchor` |
| evidence | 数组，每项 `id` / `quote`（原文短引，逐字保留）/ `anchor` / `source_type`（material/figure/table/ocr/inference）/ `relation`（direct/indirect）/ `span_start` / `span_end` |
| provenance | 数组，每项 `id` / `title` / `authors` / `year` / `version` / `identifier`（DOI、arXiv、URL 等）/ `source_path` / `anchor`；未知字段写 `unknown` 并进 uncertainties |
| relation_vocabulary | 对象，记录本次使用的受控谓词表、每个谓词的判定条件与来源；不把关系方向写反 |
| quality_checks | 数组，每项 `check` / `target_id` / `result`（pass/fail/na）/ `reason` / `anchor`；覆盖过宽、证据不足、主体混淆、关系错误、来源缺失、重复断言 |
| dedup_record | 数组，每项 `kept_id` / `merged_ids` / `rule` / `reason`，记录合并或拆分依据 |
| evidence_map | 数组，每项 `claim` / `value` / `evidence` / `anchor` / `source_type` / `change_record`；**不得写推断或常识作为证据** |
| verification | 对象，每项含 `result`（pass/fail/na）与**带计数或抽查片段**的 `evidence`，项目见 `resources/checklist.md` |
| uncertainties | 数组，每项 `item` / `reason` / `anchor` / `question_for_author`；无证据支撑、原文冲突、跨图表证据、元数据缺失分别写明 |
| sources | 使用的输入文件路径、页码/段号/图表号与版本，界定输入边界 |
| change_log | 按顺序记录问题 / 修正 / 位置 / 复核结果 |

**锚点格式**：`p<页>:<段>`、`p<页>:fig<号>`、`p<页>:tab<号>`、`p<页>:eq<号>`、`section:<章节>:<段>`、`ref:<编号>`。必须指向真实材料位置；无法定位的条目写入 uncertainties，不填伪造锚点。每个 `text` 短引必须能在对应锚点找到逐字片段。

## 工作流

### 第 0 步：落盘骨架（先保底）
读 `/input/case.json` 与 `/input/task.md`，确认 `case_id`、`output_contract`、材料路径与任务边界；在 `/app/work` 建工作副本，立即向 `/app/output/result.json` 写入 `case_id`、`status: partial`、各必填字段空数组/空对象的骨架，后续逐段增量更新。

### 第 1 步：确认输入边界与来源元数据
打开全部真实材料（正文、摘要、图表说明、参考文献页），记录 `sources`。从封面/首页/参考文献提取标题、作者、年份、版本与标识符，逐项填 `provenance`；材料中查不到的写 `unknown` 并进入 uncertainties，不用外部常识补齐。记录材料是否有文字层、是否涉及图表证据。

### 第 2 步：段落切分与候选断言生成
按 `resources/assertion_playbook.md` 的粒度判据逐段处理：一个断言只表达一个可独立判断真假的结论；并列句拆开、因果链拆开但保留关系；条件、范围、时间点、限定词、否定词写进 `qualifiers`，不得丢失。过度笼统、缺少主体的候选直接退回重拆。每条候选先落 `/app/work/candidates.jsonl`，附段落锚点。

### 第 3 步：最小充分证据绑定
为每条候选在原文中寻找**能单独支撑它的最短片段**，逐字写入 `evidence.quote` 并标 `anchor` 与 `span_start`/`span_end`。区分 `direct`（原文直接陈述）与 `indirect`（由两处或多处材料共同支持），间接证据列出全部证据 ID。找不到支撑片段的断言不写进正式结果，而是写入 uncertainties 并说明缺什么；不得用"显然""常识"替代证据。

### 第 4 步：受控关系与方向校验
按 `relation_vocabulary` 把断言映射为 `subject` / `predicate` / `object`，主体与客体不得互换；单位、条件、否定作为限定词保留。对每条三元组做方向复核：把 `subject + predicate` 读一遍，确认能自然回到 `object` 与原文语义。无法归入词表的关系写入 uncertainties 并说明边界，不强行套用。

### 第 5 步：去重、合并与质量检查
执行 `resources/assertion_playbook.md` 的去重规则：语义等价的合并并记录 `dedup_record`；范围不同或条件不同的保留为不同断言。逐条运行 `quality_checks`：断言过宽、证据不足、主体混淆、关系类型错误、来源缺失、证据与断言冲突。发现冲突时并列两种说法与各自锚点，交作者确认，不擅自择一。

### 第 6 步：带计数的自检与回修
逐项核对 `resources/checklist.md`，把**计数**写进 `verification`：
- `assertion_granularity`：单一可验证断言数 / 断言总数，附抽查短句；
- `evidence_sufficiency`：有最小充分证据的断言数 / 断言总数；
- `anchor_spotcheck`：按锚点回查成功数 / 抽查数，附短引片段；
- `relation_direction`：方向正确的三元组数 / 检查数；
- `provenance_completeness`：元数据齐全的断言数 / 断言总数，缺失项进 uncertainties；
- `dedup_clean`：去重后重复断言数（必须为 0）；
- `no_new_facts`：材料外新增事实数（必须为 0）；
- `export_parseable`：`assertions.jsonld` 能被 JSON 解析器读取且字段齐全（通过项 / 检查项）。
失败项回到第 2–5 步修正并记入 `change_log`；仍无法解决则保留 `partial`，不得写成通过。

### 第 7 步：交付与复核
写出 `/app/output/result.json` 与全部导出文件，确认：`case_id` 已回填、`output_contract` 字段齐全、每条断言有证据 ID 与锚点、`verification` 每项有计数、`uncertainties` 与 `change_log` 如实填写。最终答复只做简要说明，详细证据留在产物中。

## 异常处理

| 情况 | 处理 |
|---|---|
| 断言找不到支撑片段 | 不写入正式断言，写入 uncertainties 并说明缺失范围 |
| 原文段落自相矛盾 | 并列记录两种说法与各自锚点，标 `status: partial` |
| 证据只在图表/公式中 | 标 `source_type: figure/table`，保留图号表号，无法逐字引用时说明 |
| 无文字层扫描件 | OCR 后标 `source_type: ocr` 并给置信度，关键结论需人工复核 |
| 作者/年份/版本缺失 | 填 `unknown` 并进 uncertainties，不用外部知识补造 |
| 关系无法映射 | 保留原始关系文本并写入 uncertainties，不强行套入词表 |
| 权限不足/超时 | 尽早落盘 partial，写明失败路径与已完成范围，不编造证据 |

## 资源

- `resources/assertion_playbook.md`：断言粒度判据、受控词表、证据最小充分性判据、去重与质检规则。
- `resources/checklist.md`：带计数的自检清单。
- `resources/field_dict.md`：字段字典、锚点格式与 verification 计数项。
- `resources/output_example.json`：输出结构示意（占位示例，非答案）。
- `examples/README.md`：最小调用示例（示意）。

## 最小示例

见 `examples/README.md`。示意输出仅展示字段结构，不代表任何真实科研案例的断言、证据或评测成绩。
