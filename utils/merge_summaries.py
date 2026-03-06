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
    """
    result = {
        "title": None,
        "date": None,
        "paragraphs": [],
        "max_ref_num": 0,
    }

    # 提取h1标题
    h1_match = re.search(r"<h1>(.*?)</h1>", html, re.DOTALL)
    if h1_match:
        result["title"] = h1_match.group(1).strip()

    # 尝试提取日期（YYYY-MM-DD）
    if result["title"]:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", result["title"])
        if date_match:
            result["date"] = date_match.group(1)

    # 提取所有段落
    paragraphs = re.findall(r"<p>(.*?)</p>", html, re.DOTALL)
    result["paragraphs"] = [p.strip() for p in paragraphs]

    # 找出最大的引用编号
    ref_nums = re.findall(r"\[(\d+)\]", html)
    if ref_nums:
        result["max_ref_num"] = max(int(n) for n in ref_nums)

    return result


def renumber_references(paragraph: str, offset: int) -> str:
    """
    重新编号段落中的引用
    """

    def replace_ref(match):
        old_num = int(match.group(1))
        new_num = old_num + offset
        return f"[{new_num}]"

    return re.sub(r"\[(\d+)\]", replace_ref, paragraph)


def merge_summaries(
    low_risk_summary: Optional[str],
    high_risk_summary: Optional[str],
    date: Optional[str] = None,
    category: Optional[str] = None,
    add_section_headers: bool = True,
) -> str:
    """
    合并低风险和高风险新闻摘要
    注意：标题格式不在这里强制（由 workflows/summary_generation.py 统一强制）
    """
    logger.info("开始合并摘要")

    # 如果两个摘要都为空，返回空字符串
    if not low_risk_summary and not high_risk_summary:
        logger.warning("两个摘要都为空")
        return ""

    # 如果只有一个摘要，包装成完整HTML
    if not low_risk_summary:
        logger.info("只有高风险摘要")
        high_content = extract_html_content(high_risk_summary)
        return _build_styled_html(
            title=f"{date} {category or ''}".strip(),
            low_paragraphs=[],
            high_paragraphs=high_content["paragraphs"],
            add_section_headers=add_section_headers,
            date=date,
            category=category
        )
    if not high_risk_summary:
        logger.info("只有低风险摘要")
        low_content = extract_html_content(low_risk_summary)
        return _build_styled_html(
            title=f"{date} {category or ''}".strip(),
            low_paragraphs=low_content["paragraphs"],
            high_paragraphs=[],
            add_section_headers=add_section_headers,
            date=date,
            category=category
        )

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
    high_paragraphs_renumbered = [renumber_references(p, offset) for p in high_content["paragraphs"]]
    logger.info(f"引用编号偏移量: {offset}")

    # 构建带样式的完整HTML
    merged_html = _build_styled_html(
        title=f"{date} {category or ''}".strip(),
        low_paragraphs=low_content["paragraphs"],
        high_paragraphs=high_paragraphs_renumbered,
        add_section_headers=add_section_headers,
        date=date,
        category=category
    )
    
    logger.info(f"合并完成，总段落数: {len(low_content['paragraphs']) + len(high_paragraphs_renumbered)}")
    return merged_html


def _build_styled_html(
    title: str,
    low_paragraphs: list[str],
    high_paragraphs: list[str],
    add_section_headers: bool,
    date: Optional[str] = None,
    category: Optional[str] = None,
) -> str:
    """
    构建带完整CSS样式的HTML
    """
    from datetime import datetime
    
    html_parts = []
    
    # HTML头部和样式
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            line-height: 1.8;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        h1 {
            color: #1a1a1a;
            font-size: 28px;
            font-weight: 600;
            margin: 0 0 30px 0;
            padding-bottom: 20px;
            border-bottom: 3px solid #2196F3;
        }
        h2 {
            color: #2196F3;
            font-size: 20px;
            font-weight: 600;
            margin: 35px 0 20px 0;
        }
        h2:first-of-type {
            margin-top: 0;
        }
        p {
            margin: 0 0 20px 0;
            text-align: justify;
            font-size: 16px;
            line-height: 1.8;
        }
        a {
            color: #2196F3;
            text-decoration: none;
            transition: color 0.2s;
        }
        a:hover {
            color: #1976D2;
            text-decoration: underline;
        }
        sup {
            margin: 0 2px;
        }
        sup a {
            font-size: 12px;
            padding: 1px 4px;
            background-color: #e3f2fd;
            border-radius: 3px;
            font-weight: 500;
        }
        sup a:hover {
            background-color: #bbdefb;
            text-decoration: none;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #999;
            font-size: 13px;
            text-align: center;
        }
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }
            .container {
                padding: 20px;
            }
            h1 {
                font-size: 24px;
            }
            h2 {
                font-size: 18px;
            }
            p {
                font-size: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
""")
    
    # 标题（占位，后续会被_force_h1_title替换）
    html_parts.append(f"        <h1>{title}</h1>\n")
    
    # 低风险新闻段落
    if low_paragraphs:
        if add_section_headers:
            html_parts.append("        <h2>【ds新闻】</h2>\n")
        for p in low_paragraphs:
            html_parts.append(f"        <p>{p}</p>\n")
    
    # 高风险新闻段落
    if high_paragraphs:
        if add_section_headers:
            html_parts.append("        <h2>【gemini新闻】</h2>\n")
        for p in high_paragraphs:
            html_parts.append(f"        <p>{p}</p>\n")
    
    # 页脚
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_parts.append(f"""        <div class="footer">
            <p>DailyNews 新闻摘要系统</p>
            <p>生成时间: {gen_time}</p>
        </div>
    </div>
</body>
</html>
""")
    
    return "".join(html_parts)