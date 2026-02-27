# workflows/news_pipeline.py

from ingestion.RSSclient import RSSClient
from preprocessing.filters import filter_ru
from preprocessing.dedupe import dedupe_items
from preprocessing.classify import Classify
from config import settings
from utils.logger import get_logger

logger = get_logger("news_pipeline")

DEFAULT_CATEGORIES = ["头条", "政治", "财经", "科技", "国际"]


def _load_learned_blacklist():
    """
    加载自动学习的黑名单
    
    Returns:
        dict: {keyword: {'freq': float, 'last_seen': timestamp}} 关键词及其元数据
    """
    blacklist_file = settings.DATA_DIR / "headline_blacklist.json"
    if blacklist_file.exists():
        try:
            import json
            with open(blacklist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧格式（只有频率）
                if data and isinstance(list(data.values())[0], (int, float)):
                    import time
                    return {k: {'freq': v, 'last_seen': time.time()} for k, v in data.items()}
                return data
        except Exception as e:
            logger.warning(f"加载黑名单失败: {e}")
    return {}


def _save_learned_blacklist(blacklist):
    """保存自动学习的黑名单"""
    blacklist_file = settings.DATA_DIR / "headline_blacklist.json"
    try:
        import json
        with open(blacklist_file, 'w', encoding='utf-8') as f:
            json.dump(blacklist, f, ensure_ascii=False, indent=2)
        logger.info(f"黑名单已保存，共 {len(blacklist)} 个关键词")
    except Exception as e:
        logger.error(f"保存黑名单失败: {e}")


def _extract_keywords(text):
    """
    从文本中提取关键词（简单版）
    
    Returns:
        set: 关键词集合
    """
    import re
    # 移除标点，转小写，分词
    words = re.findall(r'\b\w+\b', text.lower())
    # 过滤停用词和短词
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    keywords = {w for w in words if len(w) > 3 and w not in stop_words}
    return keywords


def _update_blacklist_from_low_scores(items_with_scores):
    """
    从低分新闻中学习黑名单
    
    策略：
    1. 频率衰减：所有现有关键词频率 × 0.95（自然淘汰）
    2. 时间衰减：超过 30 天未出现的关键词额外 × 0.9
    3. 新增关键词：频率 >0.5 加入
    4. 清理低频：频率 <0.3 删除
    5. 限制数量：最多保留 500 个关键词（性能足够）
    
    注意：不使用白名单保护，信任 LLM 的评分。
    如果包含重要关键词还得低分，说明确实不重要。
    
    Args:
        items_with_scores: [(item, score), ...] 新闻及其评分
    """
    import time
    
    # 只处理评分 <40 的新闻
    low_score_items = [item for item, score in items_with_scores if score < 40]
    
    if len(low_score_items) < 5:
        # 样本太少，不更新
        return
    
    logger.info(f"从 {len(low_score_items)} 条低分新闻中学习黑名单...")
    
    # 统计关键词在低分新闻中的出现次数
    keyword_counts = {}
    for item in low_score_items:
        title = item.get("title") or ""
        summary = (item.get("summaryText") or "")[:100]
        text = f"{title} {summary}"
        
        keywords = _extract_keywords(text)
        for kw in keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
    
    # 计算出现频率（出现在多少比例的低分新闻中）
    total_low_score = len(low_score_items)
    keyword_freq = {
        kw: count / total_low_score 
        for kw, count in keyword_counts.items()
    }
    
    # 加载现有黑名单
    blacklist = _load_learned_blacklist()
    current_time = time.time()
    
    # 1. 频率衰减（所有现有关键词）
    decay_factor = 0.95
    time_decay_threshold = 30 * 24 * 3600  # 30 天
    time_decay_factor = 0.9
    
    for kw in list(blacklist.keys()):
        entry = blacklist[kw]
        # 频率衰减
        entry['freq'] *= decay_factor
        
        # 时间衰减：超过 30 天未出现
        if current_time - entry['last_seen'] > time_decay_threshold:
            entry['freq'] *= time_decay_factor
            logger.debug(f"时间衰减: {kw} (未出现 {(current_time - entry['last_seen']) / 86400:.0f} 天)")
    
    # 2. 更新/新增关键词
    new_entries = 0
    updated_entries = 0
    for kw, freq in keyword_freq.items():
        if freq > 0.5:  # 出现在 >50% 的低分新闻中
            if kw not in blacklist:
                blacklist[kw] = {
                    'freq': freq,
                    'last_seen': current_time
                }
                new_entries += 1
                logger.info(f"新增黑名单: {kw} (频率: {freq:.2f})")
            else:
                # 更新频率（加权平均）和时间
                old_freq = blacklist[kw]['freq']
                blacklist[kw]['freq'] = old_freq * 0.7 + freq * 0.3
                blacklist[kw]['last_seen'] = current_time
                updated_entries += 1
    
    # 3. 清理低频关键词（频率 <0.3）
    removed = []
    for kw in list(blacklist.keys()):
        if blacklist[kw]['freq'] < 0.3:
            removed.append(kw)
            del blacklist[kw]
    
    if removed:
        logger.info(f"清理低频关键词: {len(removed)} 个 - {removed[:5]}...")
    
    # 4. 限制数量（保留频率最高的前 500 个）
    # 字符串匹配很快，500 个关键词不影响性能
    max_keywords = 500
    if len(blacklist) > max_keywords:
        # 按频率排序，保留前 500
        sorted_items = sorted(blacklist.items(), key=lambda x: x[1]['freq'], reverse=True)
        blacklist = dict(sorted_items[:max_keywords])
        logger.info(f"限制黑名单数量: {len(sorted_items)} → {max_keywords}")
    
    # 保存黑名单
    if new_entries > 0 or updated_entries > 0 or removed:
        _save_learned_blacklist(blacklist)
        logger.info(
            f"黑名单更新: 新增 {new_entries}, 更新 {updated_entries}, "
            f"删除 {len(removed)}, 总计 {len(blacklist)} 个关键词"
        )


def _score_with_llm(items, llm_client):
    """
    使用 LLM 批量评分新闻重要性
    
    Args:
        items: 新闻列表
        llm_client: LLM 客户端
    
    Returns:
        list: [(item, score), ...] 新闻及其评分
    """
    if not items:
        return []
    
    results = []
    batch_size = 20
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        
        # 构建 prompt
        prompt = "评估以下新闻的重要性（0-100分）。\n\n"
        prompt += "评分标准：\n"
        prompt += "- 战争/军事冲突：80-100分\n"
        prompt += "- 政治重大事件（选举、辞职、政变）：70-90分\n"
        prompt += "- 经济危机、灾难事故：70-90分\n"
        prompt += "- 一般政治/经济新闻：50-70分\n"
        prompt += "- 社会新闻、科技新闻：40-60分\n"
        prompt += "- 娱乐八卦、生活琐事：10-30分\n"
        prompt += "- 动物趣闻、美容时尚：0-20分\n\n"
        
        for idx, item in enumerate(batch, 1):
            title = item.get("title", "")
            summary = (item.get("summaryText") or "")[:150]
            prompt += f"{idx}. {title}\n"
            if summary:
                prompt += f"   摘要: {summary}\n"
            prompt += "\n"
        
        prompt += "对每条新闻返回：编号|分数\n"
        prompt += "示例：\n1|85\n2|45\n3|15\n\n严格按照格式输出："
        
        try:
            logger.info(f"LLM 评分 {len(batch)} 条新闻...")
            response = llm_client.request_gemini_flash(
                prompt=prompt,
                temperature=0.1,
                max_tokens=300
            )
            
            # 解析结果
            scores = {}
            for line in response.strip().split('\n'):
                line = line.strip()
                if not line or '|' not in line:
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    try:
                        idx = int(parts[0].strip())
                        score = int(parts[1].strip())
                        scores[idx] = score
                    except ValueError:
                        continue
            
            # 匹配回原始新闻
            for idx, item in enumerate(batch, 1):
                score = scores.get(idx, 50)  # 默认 50 分
                results.append((item, score))
            
            logger.info(f"✓ LLM 评分完成，解析 {len(scores)} 条结果")
            
        except Exception as e:
            logger.error(f"LLM 评分失败: {e}，使用默认分数")
            # 失败时使用默认分数
            for item in batch:
                results.append((item, 50))
    
    return results


def _prioritize_headlines(items, enable_llm=True, enable_learning=True):
    """
    对头条新闻按重要性排序
    
    策略：
    1. 硬规则过滤（快速）
    2. LLM 批量评分（准确）
    3. 自动学习黑名单（长期优化）
    
    Args:
        items: 新闻列表
        enable_llm: 是否启用 LLM 评分
        enable_learning: 是否启用黑名单学习
    
    Returns:
        排序后的新闻列表
    """
    # 加载自动学习的黑名单
    learned_blacklist = _load_learned_blacklist()
    
    # 1. 硬规则过滤（快速过滤明确的垃圾）
    hard_blacklist = {
        "zoo", "pet", "horoscope", "celebrity", "fashion", "beauty", "recipe",
        "动物园", "宠物", "星座", "明星", "时尚", "美容", "食谱",
        "зоопарк", "питомц", "гороскоп", "рецепт"
    }
    
    # 合并硬规则和学习的黑名单（只使用频率 >0.3 的）
    learned_keywords = {kw for kw, entry in learned_blacklist.items() if entry['freq'] > 0.3}
    all_blacklist = hard_blacklist | learned_keywords
    
    filtered_items = []
    for item in items:
        title = (item.get("title") or "").lower()
        summary = (item.get("summaryText") or "")[:100].lower()
        text = f"{title} {summary}"
        
        # 检查是否包含黑名单关键词
        if any(kw in text for kw in all_blacklist):
            continue  # 跳过
        
        filtered_items.append(item)
    
    if len(filtered_items) < len(items):
        logger.info(f"硬规则过滤：{len(items)} → {len(filtered_items)} 条（过滤 {len(items) - len(filtered_items)} 条）")
    
    # 2. LLM 批量评分
    if enable_llm and filtered_items:
        from llms.llms import LLMClient
        llm_client = LLMClient()
        
        items_with_scores = _score_with_llm(filtered_items, llm_client)
        
        # 3. 自动学习黑名单
        if enable_learning:
            _update_blacklist_from_low_scores(items_with_scores)
        
        # 按评分排序（评分高的在前）
        sorted_items = sorted(items_with_scores, key=lambda x: x[1], reverse=True)
        
        # 只返回新闻，不返回评分
        return [item for item, score in sorted_items]
    
    # 如果不启用 LLM，使用关键词评分（fallback）
    def calculate_importance_score(item):
        """
        计算新闻重要性评分（0-100）
        
        高重要性关键词：
        - 战争/冲突：war, attack, missile, strike, military
        - 政治重大事件：president, election, government, treaty
        - 经济重大事件：crisis, collapse, sanction, tariff
        - 灾难事故：disaster, earthquake, flood, crash
        
        低重要性关键词：
        - 娱乐八卦：celebrity, fashion, beauty
        - 日常琐事：tips, advice, how to
        - 动物趣闻：zoo, pet, animal (非灾难)
        """
        title = (item.get("title") or "").lower()
        summary = (item.get("summaryText") or "")[:200].lower()
        text = f"{title} {summary}"
        
        score = 50  # 基础分
        
        # 高重要性关键词（+分）
        high_importance = {
            # 战争/军事（最高优先级）
            "war": 30, "attack": 25, "missile": 25, "strike": 20, "military": 20,
            "combat": 20, "invasion": 25, "bombing": 25, "weapon": 15,
            "战争": 30, "袭击": 25, "导弹": 25, "军事": 20, "轰炸": 25,
            "войн": 30, "атак": 25, "ракет": 25, "военн": 20,
            
            # 政治重大事件
            "president": 15, "election": 15, "government": 10, "treaty": 15,
            "parliament": 10, "sanction": 15, "coup": 20, "resign": 15,
            "总统": 15, "选举": 15, "政府": 10, "制裁": 15, "辞职": 15,
            "президент": 15, "выбор": 15, "правительств": 10, "санкц": 15,
            
            # 经济重大事件
            "crisis": 15, "collapse": 20, "bankruptcy": 15, "recession": 15,
            "危机": 15, "崩溃": 20, "破产": 15, "衰退": 15,
            "кризис": 15, "крах": 20, "банкротств": 15,
            
            # 灾难事故
            "disaster": 20, "earthquake": 20, "flood": 15, "crash": 15,
            "explosion": 20, "fire": 10, "死亡": 15, "灾难": 20,
            "катастроф": 20, "землетрясен": 20, "взрыв": 20,
        }
        
        # 低重要性关键词（-分）
        low_importance = {
            # 娱乐八卦
            "celebrity": -15, "fashion": -15, "beauty": -15, "gossip": -20,
            "明星": -15, "时尚": -15, "美容": -15, "八卦": -20,
            
            # 日常琐事
            "tips": -10, "advice": -10, "how to": -10, "guide": -10,
            "建议": -10, "指南": -10, "技巧": -10,
            "совет": -10, "рекоменд": -10,
            
            # 动物趣闻（非灾难）
            "zoo": -15, "pet": -10, "cute": -15, "adorable": -15,
            "动物园": -15, "宠物": -10, "可爱": -15,
            "зоопарк": -15, "питомц": -10,
            
            # 生活琐事
            "recipe": -15, "diet": -10, "workout": -10, "horoscope": -20,
            "食谱": -15, "饮食": -10, "星座": -20,
            "рецепт": -15, "гороскоп": -20,
        }
        
        # 计算高重要性得分
        for keyword, points in high_importance.items():
            if keyword in text:
                score += points
        
        # 计算低重要性得分
        for keyword, points in low_importance.items():
            if keyword in text:
                score += points  # points 是负数
        
        # 特殊规则：标题太短通常不重要
        if len(title) < 20:
            score -= 10
        
        # 特殊规则：包含数字和地名通常更具体
        if any(char.isdigit() for char in title):
            score += 5
        
        # 限制在 0-100 范围
        return max(0, min(100, score))
    
    # Fallback：使用关键词评分
    def score_item(item):
        importance = calculate_importance_score(item)
        
        try:
            published = int(item.get("published") or 0)
        except Exception:
            published = 0
        time_score = (published % 1000000) / 10000
        
        title = item.get("title") or ""
        title_len = len(title)
        if 40 <= title_len <= 100:
            title_score = 100
        elif title_len < 40:
            title_score = title_len * 2
        else:
            title_score = max(0, 200 - title_len)
        
        return importance * 0.6 + time_score * 0.3 + title_score * 0.1
    
    return sorted(filtered_items, key=score_item, reverse=True)


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
    sorted_items = _prioritize_headlines(headline_items, 
                                         enable_llm=settings.HEADLINE_ENABLE_LLM_SCORING,
                                         enable_learning=settings.HEADLINE_ENABLE_LEARNING)
    
    kept = sorted_items[:keep_count]
    dropped = sorted_items[keep_count:]
    
    return kept, dropped


def _apply_secondary_category_limit(items, category: str, hours: int):
    """
    对次级分类（政治/财经/科技）应用水位线
    
    策略：
    - 相对宽松，允许更多新闻
    - 使用头条的 1.5 倍水位线
    
    Args:
        items: 新闻列表
        category: 分类名称
        hours: 拉取的小时数
    
    Returns:
        (kept_items, dropped_items) 保留的和被下放的新闻
    """
    total = len(items)
    
    # 使用头条的 1.5 倍水位线
    headline_low, headline_max = _calculate_headline_limits(hours)
    low_watermark = int(headline_low * 1.5)
    max_keep = int(headline_max * 1.5)
    
    if total <= low_watermark:
        logger.info(f"[{category}] 数量 {total} ≤ 低水位 {low_watermark}，全部保留")
        return items, []
    
    # 按比例保留（60%）
    keep_count = int(total * 0.6)
    keep_count = max(10, min(keep_count, max_keep))
    
    logger.info(
        f"[{category}] 数量 {total} > 低水位 {low_watermark}，"
        f"保留 {keep_count} 条，下放 {total - keep_count} 条到国际"
    )
    
    # 简单按时间排序（最新的在前）
    sorted_items = sorted(items, key=lambda x: x.get("published", 0), reverse=True)
    
    kept = sorted_items[:keep_count]
    dropped = sorted_items[keep_count:]
    
    return kept, dropped


def _apply_international_limit(items, hours: int):
    """
    对国际分类应用水位线（兜底分类）
    
    策略：
    - 使用与头条相同的水位线
    - 超过水位线的直接丢弃
    
    Args:
        items: 新闻列表
        hours: 拉取的小时数
    
    Returns:
        kept_items: 保留的新闻（丢弃的不返回）
    """
    total = len(items)
    
    # 使用与头条相同的水位线
    low_watermark, max_keep = _calculate_headline_limits(hours)
    
    if total <= low_watermark:
        logger.info(f"[国际] 数量 {total} ≤ 低水位 {low_watermark}，全部保留")
        return items
    
    # 按比例保留（60%）
    keep_count = int(total * 0.6)
    keep_count = max(8, min(keep_count, max_keep))
    
    logger.info(
        f"[国际] 数量 {total} > 低水位 {low_watermark}，"
        f"保留 {keep_count} 条，丢弃 {total - keep_count} 条"
    )
    
    # 简单按时间排序（最新的在前）
    sorted_items = sorted(items, key=lambda x: x.get("published", 0), reverse=True)
    
    return sorted_items[:keep_count]


def run_news_pipeline_all(categories=None, hours: int = 24):
    """
    多分类：一次拉取最近 hours 小时新闻 -> 过滤 -> 去重 -> 每个分类分别产出 block
    
    分层过滤策略：
    1. 头条（最严格）：按重要性保留，不够重要的下放到次级分类
    2. 政治/财经/科技（次级）：相对宽松（1.5倍水位线），过于不重要的下放到国际
    3. 国际（兜底）：与头条同级水位线，完全不重要的直接丢弃
    """
    categories = categories or DEFAULT_CATEGORIES
    rss = RSSClient()
    data = rss.get_news(hours=hours)
    filtered = filter_ru(data)
    deduped = dedupe_items(filtered)
    raw_items = deduped.get("items", [])

    blocks = []
    dropped_from_headline = []  # 从头条下放的
    dropped_from_secondary = []  # 从次级分类下放的
    
    # 定义次级分类
    secondary_categories = ["政治", "财经", "科技"]
    
    # 第一轮：处理所有分类
    for cat in categories:
        classifier = Classify(category=cat)
        block = classifier._process_headlines(raw_items)
        
        # 特殊处理头条
        if cat == "头条":
            original_count = len(block["items"])
            kept_items, dropped_items = _apply_headline_limit(block["items"], hours)
            
            block["items"] = kept_items
            dropped_from_headline = dropped_items
            
            if dropped_items:
                logger.info(f"[头条] 保留 {len(kept_items)}/{original_count} 条，下放 {len(dropped_items)} 条到次级分类")
        
        block["category"] = cat
        blocks.append(block)
    
    # 第二轮：将头条下放的新闻重新分类到次级分类
    if dropped_from_headline:
        logger.info(f"重新分类 {len(dropped_from_headline)} 条下放的头条到次级分类...")
        
        for cat in secondary_categories:
            classifier = Classify(category=cat)
            
            # 对下放的头条进行分类
            for item in dropped_from_headline:
                predicted_category, confidence = classifier._classify_item(item)
                
                # 如果匹配当前分类且置信度足够，加入
                if predicted_category == cat and confidence >= settings.CLASSIFY_CONFIDENCE_THRESHOLD:
                    # 找到对应的 block 并添加
                    for block in blocks:
                        if block["category"] == cat:
                            block["items"].append(item)
                            break
        
        # 统计接收情况
        for block in blocks:
            if block["category"] in secondary_categories:
                logger.info(f"[{block['category']}] 接收头条下放后共 {len(block['items'])} 条")
    
    # 第三轮：对次级分类应用水位线，下放到国际
    for block in blocks:
        if block["category"] in secondary_categories:
            original_count = len(block["items"])
            kept_items, dropped_items = _apply_secondary_category_limit(
                block["items"], block["category"], hours
            )
            
            block["items"] = kept_items
            dropped_from_secondary.extend(dropped_items)
            
            if dropped_items:
                logger.info(
                    f"[{block['category']}] 保留 {len(kept_items)}/{original_count} 条，"
                    f"下放 {len(dropped_items)} 条到国际"
                )
    
    # 第四轮：将次级分类下放的新闻加入国际，并应用国际水位线
    if dropped_from_secondary:
        logger.info(f"将 {len(dropped_from_secondary)} 条次级分类下放的新闻加入国际...")
        
        # 找到国际分类的 block
        for block in blocks:
            if block["category"] == "国际":
                original_count = len(block["items"])
                block["items"].extend(dropped_from_secondary)
                logger.info(f"[国际] 接收次级下放后从 {original_count} 条增加到 {len(block['items'])} 条")
                
                # 应用国际水位线
                kept_items = _apply_international_limit(block["items"], hours)
                discarded_count = len(block["items"]) - len(kept_items)
                block["items"] = kept_items
                
                if discarded_count > 0:
                    logger.info(f"[国际] 应用水位线后保留 {len(kept_items)} 条，丢弃 {discarded_count} 条")
                break
    else:
        # 即使没有下放，也对国际应用水位线
        for block in blocks:
            if block["category"] == "国际":
                original_count = len(block["items"])
                kept_items = _apply_international_limit(block["items"], hours)
                discarded_count = original_count - len(kept_items)
                block["items"] = kept_items
                
                if discarded_count > 0:
                    logger.info(f"[国际] 应用水位线后保留 {len(kept_items)} 条，丢弃 {discarded_count} 条")
                break
    
    # 最终统计
    logger.info("=" * 60)
    logger.info("分层过滤最终结果：")
    for block in blocks:
        logger.info(f"  [{block['category']}]: {len(block['items'])} 条")
    logger.info("=" * 60)
    
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
