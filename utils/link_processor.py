# utils/link_processor.py
"""摘要链接处理工具：
把 LLM 生成的引用标记 [N] 替换为真实新闻链接，
并确保每条新闻段落只在最后一个标点之前挂上一个链接。
"""

from __future__ import annotations
import re
from typing import Any
from utils.logger import get_logger

logger = get_logger("link_processor")

# 认为这些标点是结尾标点
_PUNCT = "。！？；,.!?;"

def process_summary_links(summary_html: str, refs: list[dict[str, Any]]) -> str:
    """处理摘要中的引用链接，将 [N] 替换为实际的新闻链接，并把链接挪到段落最后一个标点前。

    Args:
        summary_html: LLM 生成的 HTML 摘要（可能包含 [1] [2] … 格式引用）
        refs: 引用列表，格式 [{"n": 1, "title": "...", "url": "..."}, …]

    Returns:
        str: 处理后的 HTML
    """
    if not summary_html:
        return summary_html

    if not refs:
        logger.warning("没有提供引用数据，跳过链接处理")
        return summary_html

    # 1) 构建编号到 URL 的映射
    ref_map: dict[int, str] = {}
    for ref in refs:
        try:
            n = ref.get("n")
            url = ref.get("url")
            if isinstance(n, int) and isinstance(url, str) and url:
                ref_map[n] = url
        except Exception:
            continue

    if not ref_map:
        logger.warning("引用列表中没有有效的 URL")
        return summary_html

    # 2) 把 [N] 替换成标准 HTML 链接 <a href="…">[N]</a>
    def _to_html_link(m: re.Match) -> str:
        n = int(m.group(1))
        url = ref_map.get(n)
        if not url:
            return m.group(0)  # 找不到 URL，保持原样
        # target="_blank" 可选，不影响布局
        return f'<a href="{url}" target="_blank">[{n}]</a>'

    # 先转换所有 [N]
    converted = re.sub(r"\[(\d+)\]", _to_html_link, summary_html)

    # 3) 分段处理：按 <p>…</p> 或按换行两次分块
    # 优先按 <p> 标签分开
    parts = re.split(r'(<p[^>]*>.*?</p>)', converted, flags=re.DOTALL)
    output = []

    for part in parts:
        # 这个片段里找所有 HTML 链接
        links = list(re.finditer(r'<a\s+href="[^"]+"\s*target="_blank">.*?</a>', part, flags=re.DOTALL))
        if len(links) <= 1:
            # 0 或 1 个链接直接保留
            output.append(part)
            continue

        # 取最后一个链接
        last_link_html = links[-1].group(0)

        # 删除所有链接（保留内部文字）
        def strip_link(m: re.Match) -> str:
            inner = re.sub(r'<a\s+href="[^"]+"\s*target="_blank">(.*?)</a>', r"\1", m.group(0), flags=re.DOTALL)
            return inner

        text_without_links = re.sub(r'<a\s+href="[^"]+"\s*target="_blank">.*?</a>', strip_link, part, flags=re.DOTALL)

        # 找到最后一句结尾标点
        m_end = re.search(rf'([{re.escape(_PUNCT)}])(?=[^{re.escape(_PUNCT)}]*$)', text_without_links)
        if m_end:
            idx = m_end.end()
            new_part = text_without_links[:idx] + last_link_html + text_without_links[idx:]
        else:
            # 没找到标点，就放到整段末尾
            new_part = text_without_links + last_link_html

        output.append(new_part)

    result_html = "".join(output)

    # 统计信息
    total_refs = len(re.findall(r"\[\d+\]", summary_html))
    kept_links = len(re.findall(r'<a\s+href=', result_html))
    logger.info(f"链接处理完成: 原始引用 {total_refs} 个，最终链接 {kept_links} 个")

    return result_html