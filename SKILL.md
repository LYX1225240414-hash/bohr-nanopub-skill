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

`check --np` 读取的 `evidence` 允许三种形态，脚本会先归一再生效：对象 `{"quote":…, "anchor":…}`、对象数组（取第一项有效记录）、纯字符串（视作 quote，`anchor` 另找 `locator`/`source`）。写成数组或字符串不会中断核验，但**只有 quote 才参与数值与用词比对**，所以正式产物仍按上表写成对象。

### 第 4 步：受控关系与方向校验
按 `relation_vocabulary` 把断言映射为 `subject` / `predicate` / `object`，主体与客体不得互换；单位、条件、否定作为限定词保留。对每条三元组做方向复核：把 `subject + predicate` 读一遍，确认能自然回到 `object` 与原文语义。无法归入词表的关系写入 uncertainties 并说明边界，不强行套用。

### 第 5 步：去重、合并与质量检查

**先跑机械检查，再人工判读**（断言粒度、证据贴合度、元数据完整性都可以机械化）：

```bash
A=/skills/weekly-skill/resources/scripts/assert_lint.py
python3 "$A" schema --out /app/work/np_schema.json
python3 "$A" check  --np /app/work/nanopubs.json --out /app/work
cat /app/work/assert_report.md
```

把工作版断言数组写到 `/app/work/nanopubs.json`（结构见 `resources/output_example.json`）后运行 `check`。按报告逐项修：

| 报告项 | 含义 | 动作 |
|---|---|---|
| `compound` | 含"并且/同时/以及/as well as"等并列连接词 | 拆成多条单一命题，或把并列项显式写进 subject/object |
| `too_long` | 断言过长（>120 字/45 词） | 拆分为多条 |
| `causal_unmarked` | 含"因此/导致/therefore"但未标 inferred | 拆成 cause 与 effect 两条；effect 标 `strength: inferred` 直到有机制证据 |
| `overbroad` | 含"所有/总是/never/all"且无 condition | 加 condition 限定，或改掉绝对化表述并降 confidence |
| `vague_unmarked` | 含"可能/部分/may/some"但 confidence 为空 | 补 confidence 并写入 uncertainties |
| `missing_evidence` | 缺 quote 或 anchor | 补最小片段与位置；补不出改 `status: uncertain` |
| `weak_alignment` | 证据与断言关键词重合 <0.30 | 换更贴切的片段，或修正断言主体 |
| `number_unsupported` | **断言里的数值在证据片段中找不到**（如断言 200 mAh/g、原文 160 mAh/g） | 逐数核对：笔误就改，换源就补新证据；无法确认则该条 `status: uncertain` 并写入 uncertainties。这是断言型产物最致命的错误，不能因词面相似而放过 |
| `cross_lingual` | 断言与证据语言不同且无共同数字/专名 | **人工核对**是否支撑；核对结论写进 uncertainties |
| `not_minimal` | 证据远长于断言 | 裁到只保留支撑该断言的最小片段 |
| `missing_metadata` | 缺 paper/year | 补齐；缺失项填 `unknown` 并进 uncertainties，不外部补造 |

`split` 子命令可对单个长句给出候选拆分点（辅助第 2 步）：
```bash
python3 "$A" split --text "<待拆长句>"
```

之后再做脚本做不到的人工判断：语义等价去重（`dedup_record`）、关系词表映射的合理性、证据是否真的支持该断言的**语义**（脚本只能测关键词与数字锚点，测不了语义蕴含）。

### 第 6 步：带计数的自检与回修
逐项核对 `resources/checklist.md`，把**计数**写进 `verification`（优先采用 `assert_report.json` 的 `verification_hint`）：
- `assertion_granularity`：单一可验证断言数 / 断言总数（取 `total - too_long - compound`）；
- `evidence_sufficiency`：有最小充分证据的断言数 / 断言总数（取 `evidence_coverage`）；
- `anchor_spotcheck`：按锚点回查成功数 / 抽查数，附短引片段；
- `relation_direction`：方向正确的三元组数 / 检查数；
- `provenance_completeness`：元数据齐全的断言数 / 断言总数（`source_traceability`）；
- `dedup_clean`：去重后重复断言数（`duplicate` 必须为 0）；
- `no_new_facts`：材料外新增事实数（必须为 0）；
- `export_parseable`：`assertions.jsonld` 能被 JSON 解析器读取且字段齐全（`structural_validity` 应为 1.0）。
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

- `resources/scripts/assert_lint.py`：**执行内核**。`schema` 导出断言/证据/来源字段约定；`check` 检出复合断言、断言过宽、因果未标、缺证据、证据不贴合、非最小片段、元数据缺失、重复与结构问题；`split` 给出长句候选拆分点。纯标准库，无第三方依赖。
- `environment/resources.yaml`：资源清单、依赖、运行时与产物说明。
- `resources/assertion_playbook.md`：断言粒度判据、受控词表、证据最小充分性判据、去重与质检规则。
- `resources/checklist.md`：带计数的自检清单。
- `resources/field_dict.md`：字段字典、锚点格式与 verification 计数项。
- `resources/output_example.json`：输出结构示意（占位示例，非答案）。
- `examples/README.md`：最小调用示例（示意）。

## 最小示例（示意，非真实案例结果）

```bash
A=/skills/weekly-skill/resources/scripts/assert_lint.py
python3 "$A" schema --out /app/work/np_schema.json
python3 "$A" check  --np /app/work/nanopubs.json --out /app/work
python3 "$A" split  --text "该方法提高了导电性，同时降低了成本，因此具有工业前景"
```

示意输出（仅结构）：

```json
{"total": 18, "evidence_coverage": 1.0, "avg_alignment": 0.62,
 "counts": {"compound": 0, "overbroad": 0, "missing_evidence": 0, "cross_lingual": 2}}
```

真正的断言必须来自本次实际运行，示意输出不得冒充正式案例答案或评测成绩。
