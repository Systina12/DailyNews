"""
摘要链接后处理工具
"""

import re
from utils.logger import get_logger

logger = get_logger("link_processor")


def process_summary_links(summary_html, refs):
    """
    处理摘要中的引用链接，将 #refN 替换为实际的新闻链接

    Args:
        summary_html: LLM 生成的 HTML 摘要，包含 <a href="#refN">[N]</a> 格式的引用
        refs: 引用列表，格式 [{"n": 1, "title": "...", "url": "..."}, ...]

    Returns:
        str: 处理后的 HTML 摘要，引用链接已替换为实际 URL

    Example:
        >>> refs = [{"n": 1, "title": "News", "url": "https://example.com"}]
        >>> html = '<p>Some text <a href="#ref1">[1]</a></p>'
        >>> process_summary_links(html, refs)
        '<p>Some text <a href="https://example.com" target="_blank">[1]</a></p>'
    """
    if not summary_html:
        return summary_html

    if not refs:
        logger.warning("没有提供引用数据，跳过链接处理")
        return summary_html

    # 创建编号到URL的映射
    ref_map = {ref["n"]: ref["url"] for ref in refs if ref.get("url")}

    if not ref_map:
        logger.warning("引用列表中没有有效的URL")
        return summary_html

    # 替换 <a href="#refN">[N]</a> 为实际链接
    def replace_ref(match):
        n_str = match.group(1)
        bracket_n_str = match.group(2)

        # 验证两个数字是否一致
        if n_str != bracket_n_str:
            logger.warning(f"引用标记不一致: href中为{n_str}，括号中为{bracket_n_str}")

        n = int(n_str)
        url = ref_map.get(n)

        if not url:
            logger.warning(f"未找到编号 {n} 对应的URL，保持原引用格式")
            return match.group(0)  # 保持原样

        return f'<a href="{url}" target="_blank">[{n}]</a>'

    # 匹配 <a href="#refN">[N]</a> 格式
    # 捕获组1: href中的数字，捕获组2: 括号中的数字
    processed = re.sub(
        r'<a href="#ref(\d+)">\[(\d+)\]</a>',
        replace_ref,
        summary_html
    )

    # 统计替换次数
    original_refs = len(re.findall(r'<a href="#ref\d+">\[\d+\]</a>', summary_html))
    processed_refs = len(re.findall(r'<a href="[^#][^"]*" target="_blank">\[\d+\]</a>', processed))

    logger.info(f"链接处理完成: 原始引用 {original_refs} 个，成功替换 {processed_refs} 个")

    return processed
