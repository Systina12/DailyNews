# utils/link_processor.py
"""
摘要链接后处理工具

目标：
1) 将 LLM 生成的引用标记 [N] 替换为真实新闻 URL 的超链接
2) 超链接只出现在"每条新闻（每个<p>段落）最后一个标点后面"
   - 段落中间不出现链接标
   - 若一个段落内有多个引用，则全部汇总到段落末尾标点之后
"""

from __future__ import annotations

import re
from typing import Any

from utils.logger import get_logger

logger = get_logger("link_processor")

# 认为"句末/段末"的常见标点（中英）
_END_PUNCT = "。！？；.!?;"


def process_summary_links(summary_html: str, refs: list[dict[str, Any]]):
    """
    处理摘要中的引用链接：
    - 将 [N] 替换为 <sup><a href="...">[N]</a></sup>
    - 对每个 <p>...</p> 段落：把段落中的所有引用链接汇总到最后一个标点之后

    Args:
        summary_html: LLM 生成的 HTML/Markdown 摘要，包含 [N] 引用
        refs: 引用列表，格式 [{"n": 1, "title": "...", "url": "..."}, ...]

    Returns:
        str: 处理后的摘要
    """
    if not summary_html:
        return summary_html

    if not refs:
        logger.warning("没有提供引用数据，跳过链接处理")
        return summary_html

    # 建立编号到 URL 的映射
    ref_map: dict[int, str] = {}
    for ref in refs:
        try:
            n = ref.get("n")
            url = ref.get("url")
            if isinstance(n, int) and url:
                ref_map[n] = str(url)
        except Exception:
            continue

    if not ref_map:
        logger.warning("引用列表中没有有效的URL，跳过链接处理")
        return summary_html

    # 1) 把 [N] 替换成超链接（先原地替换，后续再统一挪到段末）
    def _replace_bracket_ref(match: re.Match) -> str:
        n_str = match.group(1)
        try:
            n = int(n_str)
        except ValueError:
            return match.group(0)

        url = ref_map.get(n)
        if not url:
            logger.warning(f"未找到编号 {n} 对应的URL，保持原引用格式")
            return match.group(0)

        # 用 sup 做成小角标风格；显示文本仍然是 [N]
        return (
            f'<sup><a href="{url}" target="_blank" rel="noopener noreferrer">[{n}]</a></sup>'
        )

    processed = re.sub(r"\[(\d+)\]", _replace_bracket_ref, summary_html)

    # 2) 仅在每条新闻（每个<p>段落）最后一个标点后放链接
    link_pat = re.compile(
        r'<sup>\s*<a\s+[^>]*>\[\d+\]</a>\s*</sup>',
        flags=re.IGNORECASE,
    )

    p_pat = re.compile(r"(<p\b[^>]*>)(.*?)(</p>)", flags=re.IGNORECASE | re.DOTALL)

    def _move_links_to_paragraph_end(m: re.Match) -> str:
        p_open, inner, p_close = m.group(1), m.group(2), m.group(3)

        links = link_pat.findall(inner)
        if not links:
            return m.group(0)

        # 去重：使用set去除重复的链接（保持顺序）
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        if len(links) != len(unique_links):
            logger.info(f"段落中发现重复链接: 原始{len(links)}个，去重后{len(unique_links)}个")

        # 去掉段落中间的所有链接
        inner_wo = link_pat.sub("", inner)

        # 清理多余空白（避免删链接后留下奇怪空格）
        inner_wo = re.sub(r"[ \t]{2,}", " ", inner_wo)
        inner_wo = re.sub(r"\s+\n", "\n", inner_wo).strip()

        links_str = "".join(unique_links)

        # 在"最后一个标点"后面插入 links
        # 优先匹配段落末尾的标点（允许标点后有空白）
        end_punct_re = re.compile(rf"([{re.escape(_END_PUNCT)}])(\s*)$", flags=re.DOTALL)
        mm = end_punct_re.search(inner_wo)

        if mm:
            punct = mm.group(1)
            tail_ws = mm.group(2)
            prefix = inner_wo[: mm.start(1)]
            new_inner = f"{prefix}{punct}{links_str}{tail_ws}"
        else:
            # 没找到结尾标点：直接追加到末尾（尽量不改变原文）
            new_inner = f"{inner_wo}{links_str}"

        return f"{p_open}{new_inner}{p_close}"

    processed = p_pat.sub(_move_links_to_paragraph_end, processed)

    # 3) 统计替换次数（粗略）
    original_refs = len(re.findall(r"\[\d+\]", summary_html))
    replaced_refs = len(link_pat.findall(processed))
    logger.info(f"链接处理完成: 原始引用 {original_refs} 个，生成链接 {replaced_refs} 个（段末聚合）")

    return processed
