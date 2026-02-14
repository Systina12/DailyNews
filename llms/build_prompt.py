import datetime


# ========== 工具函数 ==========

def _clean_text(s):
    """清洗文本：去除多余空格"""
    return " ".join(str(s or "").split())


def _extract_summary(item):
    """提取新闻摘要内容"""
    summary = item.get("summary", "")
    if isinstance(summary, dict):
        return summary.get("content", "")
    return summary or ""


def _get_item_risk(item, risk_map, index):
    """获取新闻条目的风险等级"""
    risk = item.get("ds_risk")
    if not risk and risk_map:
        key = str(item.get("id") or (index + 1))
        risk = risk_map.get(key)
    return risk


def _filter_by_risk(items, risk_map, risk_filter):
    """根据风险等级过滤新闻"""
    return [
        item for i, item in enumerate(items)
        if _get_item_risk(item, risk_map, i) == risk_filter
    ]


# ========== Prompt 模板 ==========

RISK_ASSESSMENT_TEMPLATE = """你是一个"DeepSeek 风控失败概率判定器"。

下面是一组国际新闻条目，每一条都有唯一编号，并包含标题与摘要。
你的任务是：逐条判断，如果把该条新闻交给 DeepSeek 模型进行改写或重组，
是否"很可能触发 DeepSeek 的内容安全机制，从而导致 DeepSeek 完全不返回任何内容"。

判定原则（非常重要）：
- 你判断的是 DeepSeek 是否会失败，而不是新闻是否敏感
- 【以摘要内容为主要依据】，标题仅作辅助参考
- 不需要考虑 Gemini 的风控规则
- 不需要解释原因

请重点参考 DeepSeek 的常见失败模式，例如：
- 明显的违反中共主张的"统一"、"团结"等
- 明显的对中国大陆和中共的抹黑

【输出要求（必须严格遵守）】：
- 只输出若干行纯文本
- 每行一条
- 格式必须是：编号:low 或 编号:high
- 不要输出任何其他文字、标点或说明
- 不要输出任何解释或多余字段

示例输出格式：
1:low
2:high
3:low

下面是需要判定的新闻条目：

{news_items}"""


HEADLINE_TEMPLATE = """你是一名严谨的新闻编辑，请用中文撰写【头条】栏目（日期：{date}）。
【写作要求】
1) 只写"头条"栏目
2) 行文克制、中性，不评论、不预测、不下结论
3) 不可以选择性使用素材，必须覆盖所有编号

【事实规则】
- 只能依据"摘要"和"标题"中的事实进行概括
- 若摘要未明确说明结果，不得写成既成事实

【格式要求】
- 只输出 HTML
- 必须以 <h1>{date} 头条</h1> 开头
- 正文只能由若干 <p>...</p> 组成

【引用规则】
- 若引用某条新闻，必须在该段落中使用：<a href="#refN">[N]</a>
- 不得新增或改写编号

以下是可用的新闻素材：

{news_items}"""


# ========== Prompt 构建函数 ==========

def build_ds_risk_prompt(headline_block):
    """
    构建 DeepSeek 风险评估 prompt

    Args:
        headline_block: 包含 section 和 items 的新闻数据块

    Returns:
        dict: 包含 prompt 和 meta 信息，如果输入无效则返回 None
    """
    if not headline_block or headline_block.get("section") != "headline":
        return None

    news = headline_block.get("items", [])
    if not news:
        return None

    # 格式化新闻条目
    news_lines = [
        f"{i + 1}. 标题：{_clean_text(item.get('title'))}\n"
        f"   摘要：{_clean_text(_extract_summary(item))}"
        for i, item in enumerate(news)
    ]

    prompt = RISK_ASSESSMENT_TEMPLATE.format(
        news_items="\n\n".join(news_lines)
    )
    return {
        "prompt": prompt,
        "meta": {"count": len(news)}
    }


def build_headline_prompt(input_block, risk_filter="low"):
    """
    构建头条新闻生成 prompt

    Args:
        input_block: 包含 section 和 items 的新闻数据块
        risk_filter: 风险等级过滤器，"low" 或 "high"

    Returns:
        dict: 包含 prompt、refs 和 meta 信息，如果输入无效或无匹配新闻则返回 None
    """
    if not input_block or input_block.get("section") != "headline":
        return None

    date_str = (
        input_block.get("dateStr") or
        input_block.get("date") or
        datetime.datetime.utcnow().strftime("%Y-%m-%d")
    )

    all_news = input_block.get("items", [])
    risk_map = input_block.get("ds_risk_map")

    # 过滤新闻
    filtered_news = _filter_by_risk(all_news, risk_map, risk_filter)
    if not filtered_news:
        return None

    # 构造素材和引用
    refs = []
    news_lines = []

    for idx, item in enumerate(filtered_news, start=1):
        title = _clean_text(item.get("title"))
        summary = _clean_text(_extract_summary(item))
        link = item.get("link") or ""

        refs.append({"n": idx, "title": title, "url": link})
        news_lines.append(f"【{idx}】\n标题：{title}\n摘要：{summary}\n")

    prompt = HEADLINE_TEMPLATE.format(
        date=date_str,
        news_items="\n".join(news_lines)
    )

    return {
        "section": "headline",
        "dateStr": date_str,
        "prompt": prompt,
        "refs": refs,
        "meta": {
            "total": len(all_news),
            "filtered": len(filtered_news),
            "risk_filter": risk_filter,
        },
    }
