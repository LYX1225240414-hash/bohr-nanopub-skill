# 断言拆分与证据绑定操作手册（方法与判据）

本文件只给方法与判据，不含任何案例断言或证据。运行时所有结论必须来自 `/input` 下的真实材料。

## 1. 断言粒度判据（第 2 步）
一条合格断言须同时满足：
1. **单一性**：只含一个可判断真假的命题；"A 提高 X 且降低 Y"拆成两条。
2. **主体明确**：有具体研究对象（材料/方法/体系/指标），不用"它""该研究"等指代。
3. **条件保留**：条件、范围、时间点、单位、限定词、否定词原样写入 `qualifiers`，不泛化成普遍结论。
4. **可回查**：能在材料中找到对应段落/图表锚点；找不到则退回候选池，不进正式断言。

反例模式（一律退回重拆）：整段摘要充当一条断言；把作者观点写成实验事实；把"可能/趋势"写成"证明"；把多个实验结果合并成一条。

## 2. 证据最小充分性（第 3 步）
- 逐字短引：从原文截取能单独支撑断言的最短连续片段，写入 `evidence.quote`，保留数字、单位、限定词、否定。
- 位置：记录 `anchor` 与 `span_start`/`span_end`；锚点必须能在材料中定位，`quote` 必须逐字命中。
- 直接证据（`relation: direct`）：原文明确陈述该断言。
- 间接证据（`relation: indirect`）：由两处或多处材料 jointly 支持；列出全部证据 ID，并在 `confidence_basis` 写明推理链。
- 证据不足：不把推断写成事实；写入 uncertainties 并说明缺少哪类证据（数值、对照、条件、位置）。
- 跨图表证据：标 `source_type: figure/table`，保留图号表号；图片中无法逐字引用时说明，不抄猜测数值。

## 3. 来源元数据（第 1 步）
- 从材料封面/首页/参考文献提取 `title`、`authors`、`year`、`version`、`identifier`（DOI/arXiv/URL）。
- 每项附 `source_path` 与 `anchor`；材料没有就写 `unknown` 并进 uncertainties，不从外部知识补齐。
- 同一来源的多条断言共用 `provenance_id`，保证链路完整。

## 4. 受控关系词表（第 4 步）
默认词表（可按任务说明调整，调整须在 `relation_vocabulary` 记录判定条件）：
`reports` / `shows` / `increases` / `decreases` / `causes` / `correlates_with` / `is_composed_of` / `has_property` / `is_applicable_to` / `contradicts` / `is_defined_as` / `is_measured_by`。

方向校验步骤：把 `subject + predicate + object` 读成一句完整中文/英文句子；若读不通或与原文主谓宾相反，则交换检查后重新判定，不直接交换了事。关系不在词表内时保留原词并进 uncertainties，不强行套用。

## 5. 去重与合并规则（第 5 步）
- 合并：主体、谓词、客体、限定条件完全等价（表述不同但语义相同）→ 保留信息更完整的一条，其他 ID 记入 `merged_ids` 与 `rule`。
- 保留：数值不同、条件不同、范围不同、否定不同 → 视为不同断言。
- 冲突：同一主体同一条件得出相反结论 → 两条都保留，`quality_checks` 标 fail 并各附锚点，交作者确认。

## 6. 质量检查项（第 5 步）
逐条跑并记录到 `quality_checks`：`over_broad`（断言过宽）、`evidence_insufficient`、`subject_confusion`、`relation_direction`、`provenance_missing`、`duplicate`、`conflict`。每项给 `target_id`、`result`、`reason`、`anchor`。

## 7. 导出与可解析性（第 7 步）
- `assertions.jsonld` 采用 JSON-LD 风格：`@context` 说明字段含义，`@graph` 放断言/证据/来源节点；导出前用 JSON 解析器实际读取一次，把结果写入 `verification.export_parseable.evidence`。
- `output_contract` 有指定字段/路径时以合同为准，不因导出格式遗漏合同字段。

## 8. 轨迹与预算
- 64 次模型请求、900 秒、单次 16384 tokens；先落盘 partial 骨架再增量完善。
- 目标 ≥30 个真实可核验动作：逐段打开、候选生成、证据回查、锚点定位、词表映射、方向复核、去重、质检、回修各步留痕；不编造操作或证据。
