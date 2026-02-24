# utils/link_processor.py
"""摘要链接后处理工具

将 LLM 生成的引用标记 [N] 替换为真实新闻链接，并把链接移动到紧邻标点之后：
例如：'……[1]。' -> '……。<a ...>[1]</a>'
"""

from __future__ import annotations

import re
from typing import Any

from utils.logger import get_logger

logger = get_logger("link_processor")


# 需要把链接放到这些标点后面（中英文常见结尾标点）
_PUNCT = "。！？；,.!?;“”'()"


def process_summary_links(summary_html: str, refs: list[dict[str, Any]]):
    """处理摘要中的引用链接，将 [N] 替换为实际的新闻链接，并把链接挪到结尾标点后面。

    Args:
        summary_html: LLM 生成的 HTML/Markdown 摘要，包含 [N] 格式引用
        refs: 引用列表，格式 [{"n": 1, "title": "...", "url": "..."}, ...]
    Returns:
        str: 处理后的摘要
    """
    if not summary_html:
        return summary_html

    if not refs:
        logger.warning("没有提供引用数据，跳过链接处理")
        return summary_html

    # 创建编号到 URL 的映射
    ref_map = {}
    for ref in refs:
        try:
            n = ref.get("n")
            url = ref.get("url")
            if isinstance(n, int) and url:
                ref_map[n] = str(url)
        except Exception:
            continue

    if not ref_map:
        logger.warning("引用列表中没有有效的URL")
        return summary_html

    # 1) 替换 [N] 为 <a href="...">[N]</a>
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

        # 生成超链接 <a href="...">[N]</a>
        return (
            f'<a class="news-ref" href="{url}" target="_blank" '
            f'rel="noopener noreferrer">[{n}]</a>'
        )

    # 处理替换，去掉嵌套的链接
    processed = re.sub(r"\[(\d+)\]", _replace_bracket_ref, summary_html)

    # 2) 确保链接出现在标点符号后面
    #    '...<a ...>[1]</a>。' -> '...。<a ...>[1]</a>'
    processed = re.sub(
        rf'(<a class="news-ref"[^>]*>\[\d+\]</a>)([{re.escape(_PUNCT)}])',
        r"\2\1",
        processed,
    )

    # 统计替换次数（粗略）
    original_refs = len(re.findall(r"\[\d+\]", summary_html))
    replaced_refs = len(re.findall(r'<a class="news-ref"[^>]*>\[\d+\]</a>', processed))
    logger.info(f"链接处理完成: 原始引用 {original_refs} 个，成功替换 {replaced_refs} 个")

    return processed