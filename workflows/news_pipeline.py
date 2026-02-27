# workflows/news_pipeline.py

from ingestion.RSSclient import RSSClient
from preprocessing.filters import filter_ru
from preprocessing.dedupe import dedupe_items
from preprocessing.classify import Classify
from config import settings
from utils.logger import get_logger

logger = get_logger("news_pipeline")

DEFAULT_CATEGORIES = ["头条", "政治", "财经", "科技", "国际"]


def _prioritize_headlines(items):
    """
    对头条新闻按重要性排序
    
    排序依据（优先级从高到低）：
    1. 发布时间（越新越重要）
    2. 标题长度（适中的更重要，太短或太长都不好）
    
    Returns:
        排序后的新闻列表
    """
    def score_item(item):
        # 发布时间（主要因素）
        try:
            published = int(item.get("published") or 0)
        except Exception:
            published = 0
        
        # 标题长度（次要因素）
        title = item.get("title") or ""
        title_len = len(title)
        
        # 理想长度 40-100 字符，偏离扣分
        if 40 <= title_len <= 100:
            length_score = 100
        elif title_len < 40:
            length_score = title_len * 2  # 太短扣分多
        else:
            length_score = max(0, 200 - title_len)  # 太长扣分少
        
        # 综合评分：时间权重 90%，长度权重 10%
        return published * 0.9 + length_score * 0.1
    
    return sorted(items, key=score_item, reverse=True)


def _calculate_headline_limits(hours: int):
    """
    根据拉取的时间范围动态计算头条保留参数
    
    使用平方根函数实现次线性增长：
    - 水位线 = 基准值 × √(实际小时数 / 基准小时数)
    - 导数递减，符合阅读耐心不会线性增长的特点
    
    Args:
        hours: 拉取的小时数（如 1=每小时报, 8=每8小时报）
    
    Returns:
        (low_watermark, max_keep) 低水位和最大保留数
    
    示例：
        1小时   → √1 = 1.0×  → 低水位 10, 最大 20
        4小时   → √4 = 2.0×  → 低水位 20, 最大 40
        8小时   → √8 = 2.8×  → 低水位 28, 最大 56
        16小时  → √16 = 4.0× → 低水位 40, 最大 80
        24小时  → √24 = 4.9× → 低水位 49, 最大 98
    
    对比线性增长：
        8小时：线性8×(80) vs 平方根2.8×(28) - 降低65%
    """
    import math
    
    # 计算时间倍数（平方根）
    time_ratio = hours / settings.HEADLINE_BASE_HOURS
    time_multiplier = math.sqrt(time_ratio)
    
    # 动态计算水位线（次线性缩放）
    low_watermark = int(settings.HEADLINE_BASE_LOW_WATERMARK * time_multiplier)
    max_keep = int(settings.HEADLINE_BASE_MAX_KEEP * time_multiplier)
    
    logger.info(
        f"头条动态水位：{hours}小时 = √{time_ratio:.1f} = {time_multiplier:.2f}倍基准 "
        f"→ 低水位 {low_watermark}, 最大保留 {max_keep}"
    )
    
    return low_watermark, max_keep


def _apply_headline_limit(headline_items, hours: int):
    """
    对头条新闻应用动态保留策略
    
    策略：
    - 数量 ≤ 低水位：全部保留
    - 数量 > 低水位：按比例保留，但不少于最小值，不超过最大值
    
    Args:
        headline_items: 头条新闻列表
        hours: 拉取的小时数（用于动态计算水位）
    
    Returns:
        (kept_items, dropped_items) 保留的和被下放的新闻
    """
    total = len(headline_items)
    
    # 动态计算水位线
    low_watermark, max_keep = _calculate_headline_limits(hours)
    
    if total <= low_watermark:
        # 数量少，全部保留
        logger.info(f"头条数量 {total} ≤ 低水位 {low_watermark}，全部保留")
        return headline_items, []
    
    # 数量多，按比例保留
    keep_count = int(total * settings.HEADLINE_KEEP_RATIO)
    keep_count = max(settings.HEADLINE_MIN_KEEP, min(keep_count, max_keep))
    
    logger.info(
        f"头条数量 {total} > 低水位 {low_watermark}，"
        f"按比例保留 {keep_count} 条（{settings.HEADLINE_KEEP_RATIO*100:.0f}%），"
        f"下放 {total - keep_count} 条"
    )
    
    # 按重要性排序
    sorted_items = _prioritize_headlines(headline_items)
    
    kept = sorted_items[:keep_count]
    dropped = sorted_items[keep_count:]
    
    return kept, dropped


def run_news_pipeline_all(categories=None, hours: int = 24):
    """
    多分类：一次拉取最近 hours 小时新闻 -> 过滤 -> 去重 -> 每个分类分别产出 block
    
    特殊处理：
    1. 头条数量过多时，按重要性保留部分，其余下放到其他分类
    2. 下放的头条会重新参与其他分类的分类流程
    """
    categories = categories or DEFAULT_CATEGORIES
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    filtered = filter_ru(data)
    deduped = dedupe_items(filtered)
    raw_items = deduped.get("items", [])

    blocks = []
    dropped_headlines = []  # 被下放的头条
    
    for cat in categories:
        classifier = Classify(category=cat)
        block = classifier._process_headlines(raw_items)
        
        # 特殊处理头条
        if cat == "头条":
            original_count = len(block["items"])
            kept_items, dropped_items = _apply_headline_limit(block["items"], hours)
            
            block["items"] = kept_items
            dropped_headlines = dropped_items
            
            if dropped_items:
                logger.info(f"头条保留 {len(kept_items)}/{original_count} 条，下放 {len(dropped_items)} 条到其他分类")
        
        block["category"] = cat
        blocks.append(block)
    
    # 如果有下放的头条，重新分类到其他类别
    if dropped_headlines:
        logger.info(f"重新分类 {len(dropped_headlines)} 条下放的头条...")
        
        for cat in categories:
            if cat == "头条":
                continue  # 跳过头条本身
            
            classifier = Classify(category=cat)
            
            # 对下放的头条进行分类
            for item in dropped_headlines:
                predicted_category, confidence = classifier._classify_item(item)
                
                # 如果匹配当前分类且置信度足够，加入
                if predicted_category == cat and confidence >= settings.CLASSIFY_CONFIDENCE_THRESHOLD:
                    # 找到对应的 block 并添加
                    for block in blocks:
                        if block["category"] == cat:
                            block["items"].append(item)
                            break
        
        # 统计下放后的分布
        for block in blocks:
            if block["category"] != "头条":
                logger.info(f"分类 [{block['category']}] 接收下放头条后共 {len(block['items'])} 条")
    
    return blocks


def run_news_pipeline(category: str = "头条", hours: int = 24):
    """单分类：拉取最近 hours 小时新闻 -> 过滤 -> 去重 -> 分类"""
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    filtered = filter_ru(data)
    deduped = dedupe_items(filtered)

    # 统一使用 Classify
    classifier = Classify(category=category)
    classified = classifier._process_headlines(deduped.get("items", []))
    
    # 如果是头条，应用限制
    if category == "头条":
        original_count = len(classified["items"])
        kept_items, dropped_items = _apply_headline_limit(classified["items"], hours)
        classified["items"] = kept_items
        
        if dropped_items:
            logger.info(f"头条保留 {len(kept_items)}/{original_count} 条，丢弃 {len(dropped_items)} 条")
    
    classified["category"] = category
    return classified
