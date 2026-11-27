# 自检清单（必须带计数写入 verification）

## 第 0/1 步：输入与来源
- [ ] 已读取 `/input/case.json` 与 `/input/task.md`，`case_id` 与 `output_contract` 已记录
- [ ] 骨架 `result.json` 已早期落盘并增量更新（含 `status: partial` 保底）
- [ ] 已打开全部真实材料（正文、摘要、图表说明、参考文献页），`sources` 覆盖所用范围
- [ ] `provenance` 的标题/作者/年份/版本/标识符逐项来自材料；未知写 `unknown` 并进 uncertainties
- [ ] 未用题目标签、文件名、外部常识或示例推断材料内容

## 第 2/3 步：粒度与证据
- [ ] 每条断言只表达一个可独立判断真假的结论，并列与因果已拆开
- [ ] 条件、范围、时间点、单位、限定词、否定写入 `qualifiers`，未丢失
- [ ] 每条断言有 `evidence_ids`；`evidence.quote` 是原文逐字最短片段
- [ ] 直接证据与间接证据已区分；间接证据列出全部 ID
- [ ] 找不到支撑的候选未写入正式断言，已进 uncertainties
- [ ] 计数：单一可验证断言数 / 断言总数；有最小充分证据的断言数 / 断言总数

## 第 4/5 步：关系、去重与质检
- [ ] `subject` / `predicate` / `object` 方向已逐条复核，未把主体客体互换
- [ ] 受控谓词表有判定条件；无法映射的关系进 uncertainties 而非强套
- [ ] 语义等价断言已合并并记入 `dedup_record`；条件不同的保留为不同断言
- [ ] `quality_checks` 覆盖过宽、证据不足、主体混淆、关系错误、来源缺失、冲突
- [ ] 冲突说法并列保留并各附锚点，未擅自择一
- [ ] 计数：方向正确三元组数 / 检查数；去重后重复断言数 = 0

## 第 6/7 步：带计数的证据与诚实性
- [ ] `verification` 八项均有 `result` 与带计数/片段的 `evidence`
- [ ] `anchor_spotcheck`：按锚点回查成功数 / 抽查数，附原文短引
- [ ] `provenance_completeness`：元数据齐全断言数 / 断言总数
- [ ] `no_new_facts`：材料外新增事实数（必须为 0）
- [ ] `export_parseable`：`assertions.jsonld` 可被 JSON 解析且字段齐全
- [ ] `evidence_map` 每条有原文短引与真实锚点，`source_type` 不用"推断"或"常识"
- [ ] 缺口、冲突、权限不足写入 uncertainties；回修记入 `change_log`

## 提交前检查
- [ ] `result.json` 原样回填 `case_id` 与全部 `output_contract` 字段
- [ ] `assertions.jsonld` / `evidence_map.md` / `provenance.md` / `quality_report.md` 已写盘
- [ ] 包内不含 `result.json`、正式案例答案或预制证据
- [ ] 资源为 UTF-8 文本、相对路径、无符号链接，单文件 ≤500KB、总量 ≤2MB
