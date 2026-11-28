#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assert_lint.py — Nanopublication 断言质量与证据对齐检查器（Skill 执行内核）

解决的问题：把段落拆成断言之后，最常见的问题是
  一条断言里塞了好几个命题、断言过宽（用了"所有/总是"）、
  证据片段其实不支撑该断言、来源元数据缺失、导出结构下游读不了。
这些都能机械检出。

子命令：
  check  校验 nanopubs.json → assert_report.json + assert_report.md
  split  对过长的复合句给出候选拆分点（辅助第 2 步，不自动改内容）
  schema 导出断言/证据/来源的字段约定 → np_schema.json

nanopubs.json 约定：
{
  "case_id": "...",
  "nanopublications": [{
    "id": "np1",
    "assertion": {"text": "断言原文表述", "subject": "...", "relation": "...", "object": "...",
                  "condition": "限定条件", "confidence": "high"},
    "evidence": {"quote": "最小证据片段", "anchor": "p3:L2", "source_type": "text"},
    "provenance": {"paper": "P1", "authors": ["..."], "year": 2023,
                   "version": "v1", "identifier": "doi:..."},
    "status": "asserted"
  }]
}

检出类别：
  too_long          断言过长（可能塞了多个命题）
  compound          含并列/递进连接词（疑似复合断言，应拆分）
  causal_unmarked   含因果连接词但未标 inferred / 未拆 cause-effect
  overbroad         含绝对化表述且无 condition 限定
  vague_unmarked    含模糊限定词但 confidence 为空
  missing_evidence  缺 evidence 或 anchor
  weak_alignment    证据与断言关键词重合过低（证据可能不支撑）
  not_minimal       证据片段远长于断言（不是最小充分片段）
  missing_metadata  来源元数据缺字段
  duplicate         断言文本高度重复
  id_issue          id 缺失或重复

用法：
  python3 assert_lint.py check  --np /app/work/nanopubs.json --out /app/work
  python3 assert_lint.py split  --text "长句原文" 
  python3 assert_lint.py schema --out /app/work/np_schema.json
"""

import argparse
import json
import re
import sys
from pathlib import Path


def _as_outfile(p, default_name):
    """--out 兼容层：传目录则写入目录下 default_name，传文件名则直接写该文件。"""
    path = Path(p)
    if path.is_dir() or not path.suffix:
        path = path / default_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _as_outdir(p):
    """--out 兼容层：传的是文件名时取其父目录，避免把文件路径当目录用而崩溃。"""
    path = Path(p)
    if path.suffix.lower() in (".json", ".md", ".txt", ".yaml", ".yml", ".csv", ".tex", ".bib"):
        path = path.parent if str(path.parent) not in ("", ".") else Path(".")
    path.mkdir(parents=True, exist_ok=True)
    return path

CONNECTIVES = ["并且", "同时", "以及", "而且", "此外", "另一方面", "并在此基础上",
               "as well as", "and also", "moreover", "furthermore", "in addition"]
CAUSAL = ["因此", "所以", "导致", "从而", "因而", "由此", "because", "therefore",
          "thus", "hence", "results in", "leads to", "gives rise to"]
ABSOLUTE = ["所有", "全部", "总是", "从未", "任何", "无一", "必然",
            "all ", "always", "never", "every ", "none of", "invariably", "without exception"]
VAGUE = ["可能", "大概", "或许", "某些", "部分", "若干", "约",
         "may ", "might ", "possibly", "some ", "several", "approximately", "roughly"]
STOP = set("""的 了 在 是 和 与 及 或 对 为 被 由 从 到 于 中 上 下 一个 一种 这 那 其 之 而 也 都 很
the a an of in on for to and or is are was were be been by with as at from that this these those it its
we our they their which who whom whose than then such can could may might will would""".split())

SCHEMA = {
    "assertion": {
        "required": ["text", "subject", "relation", "object"],
        "optional": ["condition", "confidence", "polarity", "quantifier"],
        "note": "text 应为单一可判断真假的命题；subject/relation/object 构成受控三元组",
    },
    "evidence": {
        "required": ["quote", "anchor"],
        "optional": ["source_type", "strength", "minimality_note"],
        "note": "quote 为最小充分片段；anchor 指向原文真实位置；source_type ∈ text/table/figure_caption",
    },
    "provenance": {
        "required": ["paper", "year"],
        "optional": ["authors", "version", "identifier", "retrieved_at"],
        "note": "paper 与 sources 标识一致；identifier 可为 doi/pmid/arxiv",
    },
    "nanopublication": {
        "required": ["id", "assertion", "evidence", "provenance", "status"],
        "status_values": ["asserted", "uncertain", "contradicted", "retracted"],
    },
    "rules": [
        "一条断言只表达一个可判断真假的命题",
        "复合句必须拆成多条断言，或把并列项显式写进 subject/object",
        "因果断言必须给出机制或标 strength=inferred",
        "绝对化断言必须有 condition 限定，否则降 confidence 或改写",
        "证据片段必须是支撑该断言的最小充分片段",
        "断言、证据、来源三者必须能串成完整链路",
    ],
}


def kw_set(text):
    t = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(text or "")).lower()
    toks = [w for w in t.split() if w and w not in STOP and len(w) > 1]
    # 中文按 2-gram 补充
    cjk = re.findall(r"[\u4e00-\u9fff]+", t)
    grams = []
    for chunk in cjk:
        if len(chunk) <= 4:
            grams.append(chunk)
        else:
            grams.extend(chunk[i:i + 2] for i in range(len(chunk) - 1))
    return set(toks) | set(grams)


def num_tokens(text):
    """跨语言可比的锚点：数字、单位、缩写、化学式、英文专名"""
    return {m.group(0).lower() for m in re.finditer(
        r"\d+(?:\.\d+)?\s*(?:%|°c|k|h|min|s|ma|mv|nm|µm|ml|mg|g|ev|wt)?|[A-Za-z][A-Za-z0-9\-]{2,}", str(text or ""))}


def numbers_only(text):
    """只取真实数值并归一（160.0→160、1e-3→0.001）。

    num_tokens 是跨语言锚点集合，混有英文词与单位，不能拿来做"数值是否被证据支持"
    的子集判断，否则会把 capacity/exhibits 这类词也算成缺失数值。
    """
    out = set()
    for m in re.finditer(r"(?<![\w.\-])([+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?)",
                         str(text or "")):
        try:
            out.add("%g" % float(m.group(1)))
        except ValueError:
            continue
    return out


def cjk_ratio(text):
    s = re.sub(r"\s", "", str(text or ""))
    if not s:
        return 0.0
    return len(re.findall(r"[\u4e00-\u9fff]", s)) / len(s)


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def get_nps(data):
    """同时支持两种结构：
    A) 嵌套：{"nanopublications": [{id, assertion:{}, evidence:{}, provenance:{}}]}
    B) 平铺：{"assertions": [...], "evidence": [...], "provenance": [...]}，靠 evidence_ids/provenance_id 关联
    """
    if isinstance(data, list):
        return data
    for k in ("nanopublications", "nanopubs", "items"):
        if isinstance(data.get(k), list):
            return data[k]
    if isinstance(data.get("assertions"), list):
        ev = {e.get("id"): e for e in (data.get("evidence") or []) if isinstance(e, dict)}
        pv = {p.get("id"): p for p in (data.get("provenance") or []) if isinstance(p, dict)}
        out = []
        for a in data["assertions"]:
            if not isinstance(a, dict):
                continue
            eids = a.get("evidence_ids") or a.get("evidence_id") or []
            if isinstance(eids, str):
                eids = [eids]
            evs = [ev.get(x) for x in eids if ev.get(x)]
            prov = pv.get(a.get("provenance_id")) or {}
            qual = a.get("qualifiers")
            if isinstance(qual, list):
                qual = "; ".join(str(x) for x in qual if str(x).strip())
            out.append({
                "id": str(a.get("id") or ""),
                "assertion": {
                    "text": a.get("text") or "",
                    "subject": a.get("subject") or "",
                    "relation": a.get("predicate") or a.get("relation") or "",
                    "object": a.get("object") or "",
                    "condition": qual or a.get("condition") or "",
                    "confidence": a.get("confidence") or "",
                },
                # 取第一条证据作为主证据；多条时合并片段与位置
                "evidence": (evs[0] if len(evs) == 1 else {
                    "quote": " … ".join(str(e.get("quote") or "") for e in evs),
                    "anchor": ", ".join(str(e.get("anchor") or "") for e in evs),
                    "source_type": evs[0].get("source_type") if evs else None,
                    "strength": evs[0].get("relation") if evs else None,
                    "extra_evidence_count": max(0, len(evs) - 1),
                }) if evs else {},
                "provenance": prov,
                "status": a.get("status") or "asserted",
            })
        return out
    return []


def cmd_check(args):
    data = load(args.np)
    if "_error" in data:
        print(json.dumps({"ok": False, "error": data["_error"]}, ensure_ascii=False))
        return 1
    nps = get_nps(data)
    if not nps:
        print(json.dumps({"ok": False, "error": "未找到 nanopublications 数组"}, ensure_ascii=False))
        return 1

    cat = {k: [] for k in ["too_long", "compound", "causal_unmarked", "overbroad",
                           "vague_unmarked", "missing_evidence", "weak_alignment",
                           "not_minimal", "missing_metadata", "duplicate", "id_issue",
                           "cross_lingual", "number_unsupported"]}
    ids, texts = set(), {}
    aligns = []

    for i, np_ in enumerate(nps, 1):
        nid = str(np_.get("id") or f"np{i}")
        if not np_.get("id"):
            cat["id_issue"].append({"id": nid, "issue": "缺 id"})
        elif nid in ids:
            cat["id_issue"].append({"id": nid, "issue": "id 重复"})
        ids.add(nid)

        a = np_.get("assertion") or {}
        text = str(a.get("text") or "")
        low = text.lower()
        if not text.strip():
            cat["id_issue"].append({"id": nid, "issue": "assertion.text 为空"})
            continue

        # 粒度
        if len(text) > 120 or len(text.split()) > 45:
            cat["too_long"].append({"id": nid, "chars": len(text),
                                    "text": text[:140],
                                    "action": "拆成多条单一命题断言"})
        hits = [c for c in CONNECTIVES if c in low]
        if hits and len(text) > 20:
            cat["compound"].append({"id": nid, "connectives": hits, "text": text[:140],
                                    "action": f"在 {hits} 处拆分，或把并列项写进 subject/object"})
        chits = [c for c in CAUSAL if c in low]
        if chits and str(np_.get("status") or "asserted") == "asserted":
            strength = str((np_.get("evidence") or {}).get("strength") or "")
            if strength != "inferred":
                cat["causal_unmarked"].append({"id": nid, "connectives": chits,
                                               "action": "拆成 cause/effect 两条断言，或标 evidence.strength=inferred",
                                               "text": text[:140]})
        ahits = [c for c in ABSOLUTE if c in low]
        if ahits and not str(a.get("condition") or "").strip():
            cat["overbroad"].append({"id": nid, "words": ahits, "text": text[:140],
                                     "action": "加 condition 限定，或改掉绝对化表述并降 confidence"})
        vhits = [c for c in VAGUE if c in low]
        if vhits and not str(a.get("confidence") or "").strip():
            cat["vague_unmarked"].append({"id": nid, "words": vhits,
                                          "action": "补 confidence（high/medium/low）并在 uncertainties 说明",
                                          "text": text[:140]})

        # 证据。evidence 可能是对象、对象数组或纯字符串，统一归一后再取字段，
        # 否则遇到数组会直接抛 AttributeError 让整次核验失败。
        ev = np_.get("evidence")
        if isinstance(ev, list):
            evs = [x for x in ev if isinstance(x, dict)]
            ev = evs[0] if evs else {}
        elif isinstance(ev, str):
            ev = {"quote": ev}
        elif not isinstance(ev, dict):
            ev = {}
        quote = str(ev.get("quote") or "")
        anchor = str(ev.get("anchor") or ev.get("locator") or ev.get("source") or "")
        if not quote.strip() or not anchor.strip():
            cat["missing_evidence"].append({"id": nid,
                                            "missing": [k for k, v in (("quote", quote), ("anchor", anchor)) if not v.strip()],
                                            "action": "补最小证据片段与原文位置；补不出则改 status=uncertain"})
        else:
            ak, ek = kw_set(text), kw_set(quote)
            nk, mk = numbers_only(text), numbers_only(quote)
            lex = len(ak & ek) / max(1, len(ak))
            anchor_hit = len(nk & mk) / max(1, len(nk)) if nk else 0.0
            cross = (cjk_ratio(text) > 0.30) and (cjk_ratio(quote) < 0.10)
            score = None
            if cross:
                # 中文断言 vs 英文证据：词汇不可比，只能用数字/专名等跨语言锚点
                if anchor_hit > 0:
                    score = 1.0
                    aligns.append(score)
                else:
                    cat["cross_lingual"].append({
                        "id": nid, "text": text[:120], "quote": quote[:120],
                        "action": "断言与证据语言不同且无共同数字/专名锚点，需人工核对是否支撑",
                    })
            else:
                score = max(lex, anchor_hit)
                aligns.append(score)
                if score < 0.30:
                    cat["weak_alignment"].append({
                        "id": nid, "overlap": round(score, 3),
                        "missing_kw": sorted(list(ak - ek))[:8],
                        "text": text[:120], "quote": quote[:120],
                        "action": "证据片段可能不支撑该断言：换更贴切的片段，或调整断言主体",
                    })
            # 数值必须能在证据里找到：词面相似会掩盖数值矛盾（断言写 200 而原文是 160），
            # 这是断言型产物最致命的错误，单独硬检查。
            if nk and not nk <= mk:
                cat["number_unsupported"].append({
                    "id": nid, "assertion_numbers": sorted(nk)[:10],
                    "evidence_numbers": sorted(mk)[:10],
                    "missing_numbers": sorted(nk - mk)[:10],
                    "text": text[:140], "quote": quote[:140],
                    "action": "断言里的数值在证据片段中找不到：核对是否笔误/换源，或把该数改为 status=uncertain 并标需人工确认",
                })
            if len(quote) > max(240, 3 * max(1, len(text))):
                cat["not_minimal"].append({"id": nid, "assertion_chars": len(text),
                                           "evidence_chars": len(quote),
                                           "action": "裁到只保留支撑该断言的最小片段"})

        # 来源
        pv = np_.get("provenance") or {}
        paper = pv.get("paper") or pv.get("title") or pv.get("source_path") or pv.get("doi")
        miss = []
        if not str(paper or "").strip():
            miss.append("paper")
        if not str(pv.get("year") or "").strip():
            miss.append("year")
        if miss:
            cat["missing_metadata"].append({"id": nid, "missing": miss,
                                            "action": "补 paper（或 title/source_path）与 year；建议同时补 authors/version/identifier"})

        # 重复
        key = re.sub(r"\s+", "", text.lower())[:60]
        if key in texts:
            cat["duplicate"].append({"id": nid, "same_as": texts[key], "text": text[:100]})
        else:
            texts[key] = nid

    total = len(nps)
    with_ev = total - len(cat["missing_evidence"])
    avg_align = round(sum(aligns) / len(aligns), 3) if aligns else 0.0
    bad_ids = {x["id"] for x in cat["id_issue"]}
    ok_np = total - len(bad_ids)
    report = {
        "ok": True, "np": str(args.np), "total": total,
        "counts": {k: len(v) for k, v in cat.items()},
        "avg_alignment": avg_align,
        "evidence_coverage": round(with_ev / total, 4) if total else 0.0,
        "structural_validity": round(max(0, ok_np) / total, 4) if total else 0.0,
        "issues": cat,
        "verification_hint": {
            "assertion_granularity": f"单一命题断言 {total - len(cat['too_long']) - len(cat['compound'])} / {total}",
            "evidence_alignment": f"证据齐备 {with_ev} / {total}；可比对项平均重合 {avg_align}；跨语言待人工 {len(cat['cross_lingual'])}",
            "source_traceability": f"元数据齐全 {total - len(cat['missing_metadata'])} / {total}",
            "structural_validity": f"无结构问题 {max(0, ok_np)} / {total}",
        },
    }
    out = _as_outdir(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "assert_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = ["# 断言质量与证据对齐报告", "",
          f"- 断言总数 {total}｜证据齐备 {with_ev}｜平均关键词重合 {avg_align}", ""]
    labels = [("断言过长（应拆）", "too_long"), ("复合断言（应拆）", "compound"),
              ("因果未标注", "causal_unmarked"), ("断言过宽", "overbroad"),
              ("模糊未标置信", "vague_unmarked"), ("缺证据/位置", "missing_evidence"),
              ("证据不贴合（重合低）", "weak_alignment"), ("证据非最小片段", "not_minimal"),
              ("跨语言需人工核对", "cross_lingual"),
              ("来源元数据缺失", "missing_metadata"), ("断言重复", "duplicate"),
              ("结构/id 问题", "id_issue")]
    for label, k in labels:
        if cat[k]:
            md += [f"## {label}（{len(cat[k])}）", ""]
            for it in cat[k][:20]:
                extra = it.get("text") or it.get("missing") or it.get("words") or it.get("connectives") or ""
                md.append(f"- `{it['id']}` {extra} → {it.get('action','')}")
            md.append("")
    md += ["## 自检口径建议", ""] + [f"- `{k}`：{v}" for k, v in report["verification_hint"].items()]
    (out / "assert_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"total": total, "evidence_coverage": report["evidence_coverage"],
                      "avg_alignment": avg_align, "counts": report["counts"]}, ensure_ascii=False))
    return 0


def cmd_split(args):
    text = args.text or ""
    if not text.strip():
        print(json.dumps({"ok": False, "error": "空文本"}, ensure_ascii=False))
        return 1
    points = []
    for c in CONNECTIVES + CAUSAL:
        start = 0
        while True:
            i = text.lower().find(c, start)
            if i < 0:
                break
            points.append({"connective": c, "pos": i,
                           "left": text[:i][-40:].strip(),
                           "right": text[i + len(c):][:40].strip()})
            start = i + len(c)
    points.sort(key=lambda x: x["pos"])
    print(json.dumps({"ok": True, "text": text, "candidate_splits": points,
                      "suggested_count": len(points) + 1,
                      "note": "拆分后每条应是单一可判断真假的命题；因果处拆成 cause 与 effect 两条，effect 标 pending 直到有机制证据"},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_schema(args):
    _p = _as_outfile(args.out, "np_schema.json")
    _p.write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(_p)}, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Nanopublication 断言质量检查器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("check"); s1.add_argument("--np", required=True); s1.add_argument("--out", required=True)
    s2 = sub.add_parser("split"); s2.add_argument("--text", required=True)
    s3 = sub.add_parser("schema"); s3.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"check": cmd_check, "split": cmd_split, "schema": cmd_schema}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
