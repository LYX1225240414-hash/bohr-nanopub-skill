---
name: nanopub-builder
description: 构建带证据与来源的纳米出版结构化断言，供 Agent 在完成 Nanopublication 任务时使用
---

# nanopub-builder：纳米出版三元组断言与证据绑定

围绕"纳米出版三元组断言与证据绑定"给出可被 Agent 稳定执行、结果可核验的工作流。核心是：读取真实输入、遵循明确规则、保留来源与证据、诚实标注不确定性。

## 何时使用
- 需要完成本题指定的学术写作/阅读任务，且要求结果能被第三方复核。
- 需要事实、数字、引用、来源可逐条回查，不新增材料外信息。

不适用：无原文材料、纯内容问答、要求编造结果的场景。

## 输入输出
输入：任务说明与科研材料（文件路径或文本）；可选约束（文体、格式、关注字段）。
输出 result.json 字段：
- case_id：输入标识，无则 N/A
- status：success / partial / unable / refused，部分完成说明原因
- 主结果：按题目要求的结构化产物
- evidence_map：事实/数字/引用/关键论断的来源与修改记录，可逐条回溯
- verification：各项自检结论
- uncertainties：材料缺失、冲突、无法判断的条目
- change_log：自检回修记录

## 工作流
### 第 1 步 读取输入边界
读取实际文件，不用标签推断内容。确认语言、格式、是否有图表公式、是否残缺。缺失 → status: unable 并说明。

### 第 2 步 建立约束与规则表
从任务说明抽取文体、格式、术语、禁止改动项，形成本次执行的规则表；规则表是执行依据，后续每步重读。

### 第 3 步 分块处理
按原文结构分块，逐块产出结果，每块附 evidence 与 anchor（页码/段落/图表/公式位置）。事实、数字、单位、引用编号、限定词、否定关系原样保留。

### 第 4 步 全篇回扫
规则表逐条回扫：术语一致性、字段/格式完整性、来源可回查性、跨章节一致性。

### 第 5 步 自检与回修
逐项核对 resources/checklist.md；发现问题回到第 3 步修正，记入 change_log。无法判断项写入 uncertainties，不猜。

### 第 6 步 输出结果
按结构写 result.json，partial 状态指明未完成范围与人工接管位置。

## 异常处理
| 情况 | 处理 |
|---|---|
| 材料缺失/无法读取 | OCR 或 status: unable，说明具体位置 |
| 图表公式为图片 | 保留占位与锚点，不猜内容 |
| 术语/规则冲突 | 分列并写清位置，写入 uncertainties |
| 超长输入 | 分块处理，save early，标注处理进度 |

## 资源
- resources/checklist.md：自检清单
- resources/field_dict.md：字段/输出约定
- resources/output_example.json：输出结构示意（非答案）
- examples/README.md：最小调用示例
