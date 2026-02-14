"""
摘要合并工具

用于合并低风险和高风险新闻的HTML摘要
"""

import re
from typing import Optional, Dict, Any
from utils.logger import get_logger

logger = get_logger("merge_summaries")


def extract_html_content(html: str) -> Dict[str, Any]:
    """
    提取HTML内容的各个部分

    Args:
        html: HTML字符串

    Returns:
        dict: 包含标题、段落和引用信息
    """
    result = {
        "title": None,
        "date": None,
        "paragraphs": [],
        "max_ref_num": 0
    }

    # 提取h1标题
    h1_match = re.search(r'<h1>(.*?)</h1>', html, re.DOTALL)
    if h1_match:
        result["title"] = h1_match.group(1).strip()
        # 尝试提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', result["title"])
        if date_match:
            result["date"] = date_match.group(1)

    # 提取所有段落
    paragraphs = re.findall(r'<p>(.*?)</p>', html, re.DOTALL)
    result["paragraphs"] = [p.strip() for p in paragraphs]

    # 找出最大的引用编号
    ref_nums = re.findall(r'\[(\d+)\]', html)
    if ref_nums:
        result["max_ref_num"] = max(int(n) for n in ref_nums)

    return result


def renumber_references(paragraph: str, offset: int) -> str:
    """
    重新编号段落中的引用

    Args:
        paragraph: 段落文本
        offset: 编号偏移量

    Returns:
        str: 重新编号后的段落
    """
    def replace_ref(match):
        old_num = int(match.group(1))
        new_num = old_num + offset
        return f'<a href="#ref{new_num}">[{new_num}]</a>'

    return re.sub(r'<a href="#ref(\d+)">\[(\d+)\]</a>', replace_ref, paragraph)


def merge_summaries(
    low_risk_summary: Optional[str],
    high_risk_summary: Optional[str],
    date: Optional[str] = None,
    add_section_headers: bool = True
) -> str:
    """
    合并低风险和高风险新闻摘要

    Args:
        low_risk_summary: 低风险新闻摘要HTML
        high_risk_summary: 高风险新闻摘要HTML
        date: 日期字符串（如果为None则从摘要中提取）
        add_section_headers: 是否添加分节标题

    Returns:
        str: 合并后的HTML摘要
    """
    logger.info("开始合并摘要")

    # 如果两个摘要都为空，返回空字符串
    if not low_risk_summary and not high_risk_summary:
        logger.warning("两个摘要都为空")
        return ""

    # 如果只有一个摘要，直接返回
    if not low_risk_summary:
        logger.info("只有高风险摘要")
        return high_risk_summary
    if not high_risk_summary:
        logger.info("只有低风险摘要")
        return low_risk_summary

    # 提取两个摘要的内容
    low_content = extract_html_content(low_risk_summary)
    high_content = extract_html_content(high_risk_summary)

    # 确定日期
    if not date:
        date = low_content["date"] or high_content["date"] or "未知日期"

    logger.info(f"合并日期: {date}")
    logger.info(f"低风险段落数: {len(low_content['paragraphs'])}")
    logger.info(f"高风险段落数: {len(high_content['paragraphs'])}")

    # 重新编号高风险摘要的引用
    offset = low_content["max_ref_num"]
    high_paragraphs_renumbered = [
        renumber_references(p, offset)
        for p in high_content["paragraphs"]
    ]

    logger.info(f"引用编号偏移量: {offset}")

    # 构建合并后的HTML
    html_parts = [f"<h1>{date} 头条</h1>"]

    # 添加低风险新闻段落
    if add_section_headers and low_content["paragraphs"]:
        html_parts.append("<p><strong>【主要新闻】</strong></p>")

    html_parts.extend(f"<p>{p}</p>" for p in low_content["paragraphs"])

    # 添加高风险新闻段落
    if add_section_headers and high_paragraphs_renumbered:
        html_parts.append("<p><strong>【其他新闻】</strong></p>")

    html_parts.extend(f"<p>{p}</p>" for p in high_paragraphs_renumbered)

    merged_html = "\n".join(html_parts)

    logger.info(f"合并完成，总段落数: {len(low_content['paragraphs']) + len(high_paragraphs_renumbered)}")

    return merged_html
