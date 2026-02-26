# preprocessing/classify.py

import os
import re
import math
from typing import Dict, List, Tuple, Optional
from llms.llms import LLMClient
from utils.logger import get_logger

logger = get_logger("classify")


class Classify:
    """
    新闻分类器
    流程：硬排除 → 分类（头条需额外检查软内容）→ 筛选
    支持5个类别：头条、政治、财经、科技、国际
    """

    def __init__(self, category):
        """
        Args:
            category: 要提取的类别（头条/政治/财经/科技/国际）
        """
        self.category = category

    def _is_hard_excluded(self, item):
        """硬排除：娱乐、体育、节目等明确不要的内容"""
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        # 安全提取链接
        link = ""
        canonical = item.get("canonical")
        if isinstance(canonical, list) and len(canonical) > 0:
            link = canonical[0].get("href", "")
        if not link:
            alternate = item.get("alternate")
            if isinstance(alternate, list) and len(alternate) > 0:
                link = alternate[0].get("href", "")
        if not link:
            link = item.get("link", "")
        link = (link or "").lower()

        # 收集所有文本
        text_parts = [
            title,
            item.get("summaryText", ""),
            item.get("summary", {}).get("content", "") if isinstance(item.get("summary"), dict) else "",
            str(item.get("summary", "")),
            link,
        ]
        full_text = " ".join(str(p) for p in text_parts if p).lower()

        hard_exclude = [
            # 节目/预告
            "sneak peek", "preview", "episode", "season",
            # 体育
            "super bowl", "nfl", "olympic", "world cup", "beat ", "wins ", "defeats ",
            "athlete", "curling", "skating",
            # 娱乐
            "music", "singer", "band", "album", "song", "eagles", "henley",
            # 展览/宠物
            "dog show", "kennel", "show where", "wins gold",
            # 电视栏目
            "60 minutes", "48 hours", "face the nation", "sunday morning",
            "the takeout", "weekend news", "almanac", "passage:",
        ]
        if any(kw in full_text for kw in hard_exclude):
            return True

        # CBS视频和文字稿
        if "cbsnews.com/video/" in link or "60-minutes-transcript" in link:
            return True

        # 美媒节目型标题（日期前缀）
        if ("cbs" in src or "bbc" in src):
            if re.match(r"^\d{1,2}/\d{1,2}", title) or re.match(r"^\d{4}:\s", title):
                return True

        return False

    def _is_soft_content(self, item):
        """软内容判断：视频、访谈、文化等（只影响"头条"分类）"""
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()

        soft_keywords = [
            "video", "interview", "transcript", "nature", "art", "museum", "culture",
            "review", "book", "film", "celebrity", "entertainment",
        ]
        if any(kw in title for kw in soft_keywords):
            return True

        # BBC软内容栏目
        if "bbc" in src and any(kw in title for kw in ["culture", "future", "travel", "worklife"]):
            return True

        # 美媒娱乐/生活
        if any(s in src for s in ["cbs", "nbc", "abc"]):
            if any(kw in title for kw in ["celebrity", "sports", "entertainment"]):
                return True

        return False

    def _classify_item(self, item):
        """
        将新闻分类到5个类别之一
        分类优先级：头条 > 政治 > 财经 > 科技 > 国际
        
        Returns:
            tuple: (category, confidence) 类别和置信度(0-1)
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 1. 头条：来源标记为top 且 不是软内容
        if ("top" in src or "top" in cats or "头条" in src or "头条" in cats):
            if not self._is_soft_content(item):
                return "头条", 0.9  # 高置信度
            else:
                return "头条", 0.5  # 软内容降低置信度

        # 2. 政治
        political_keywords = [
            "election", "vote", "parliament", "government", "president", "prime minister",
            "policy", "sanction", "cabinet", "congress", "senate", "politic",
            "选举", "政府", "总统", "议会", "内阁", "制裁",
        ]
        political_sources = ["politics", "politica"]
        
        keyword_match = sum(1 for kw in political_keywords if kw in title)
        source_match = any(s in src for s in political_sources)
        
        if keyword_match >= 2 or source_match:
            return "政治", 0.85
        elif keyword_match == 1:
            return "政治", 0.6  # 单个关键词，置信度中等

        # 3. 财经
        econ_keywords = [
            "economy", "economic", "market", "stock", "inflation", "bank", "finance", "business",
            "economia", "borsa", "mercato",
            "经济", "股市", "通胀", "银行",
        ]
        econ_sources = ["business", "economia"]
        
        keyword_match = sum(1 for kw in econ_keywords if kw in title)
        source_match = any(s in src for s in econ_sources)
        
        if keyword_match >= 2 or source_match:
            return "财经", 0.85
        elif keyword_match == 1:
            return "财经", 0.6

        # 4. 科技
        tech_keywords = [
            "tech", "technology", "ai", "artificial intelligence", "software", "chip",
            "science", "scienza",
            "科技", "人工智能", "半导体",
        ]
        tech_sources = ["tech", "science", "scienza"]
        
        keyword_match = sum(1 for kw in tech_keywords if kw in title)
        source_match = any(s in src for s in tech_sources)
        
        if keyword_match >= 2 or source_match:
            return "科技", 0.85
        elif keyword_match == 1:
            return "科技", 0.6

        # 5. 国际（兜底）
        return "国际", 0.4  # 兜底分类，置信度低

    def _batch_classify_with_llm(self, items: List[Dict], batch_size: int = 20) -> List[Dict]:
        """
        使用 LLM 批量分类新闻
        
        Args:
            items: 待分类的新闻列表
            batch_size: 每批处理的新闻数量
            
        Returns:
            List[Dict]: 分类结果列表，每项包含 {'category': str, 'is_noise': bool}
        """
        if not items:
            return []
        
        llm_client = LLMClient()
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            
            # 构建批量 prompt
            prompt = "判断以下新闻的类别和是否为噪音内容。\n\n"
            for idx, item in enumerate(batch, 1):
                title = item.get("title", "")
                summary = (item.get("summaryText") or "")[:150]
                src = item.get("origin", {}).get("title", "")
                prompt += f"{idx}. 标题: {title}\n"
                if summary:
                    prompt += f"   摘要: {summary}\n"
                if src:
                    prompt += f"   来源: {src}\n"
                prompt += "\n"
            
            prompt += """对每条新闻返回：编号|类别|是否噪音

类别选项：头条/政治/财经/科技/国际
是否噪音：yes（娱乐、体育、生活、文化类）/ no（政治、经济、科技、国际新闻）

判断标准：
- 头条：重大突发事件、高层政治动态
- 政治：选举、政府、议会、政策、制裁
- 财经：经济、市场、股市、通胀、银行
- 科技：技术、AI、软件、芯片、科学
- 国际：其他国际新闻
- 噪音：娱乐、体育、旅游、美食、时尚、天气、星座

示例输出：
1|政治|no
2|国际|no
3|头条|yes
4|财经|no

请严格按照格式输出，每行一条："""
            
            try:
                # 使用便宜的 Gemini Flash 模型
                logger.info(f"LLM 批量分类 {len(batch)} 条新闻...")
                response = llm_client.request_gemini_flash(
                    prompt=prompt,
                    temperature=0.1,  # 低温度，更确定性
                    max_tokens=500
                )
                
                # 解析结果
                for line in response.strip().split('\n'):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split('|')
                    if len(parts) >= 3:
                        results.append({
                            'category': parts[1].strip(),
                            'is_noise': parts[2].strip().lower() == 'yes'
                        })
                
                logger.info(f"✓ LLM 分类完成，解析 {len(results)} 条结果")
                
            except Exception as e:
                logger.error(f"LLM 分类失败: {e}，使用兜底策略")
                # 失败时使用兜底策略：标记为国际，不是噪音
                for _ in batch:
                    results.append({
                        'category': '国际',
                        'is_noise': False
                    })
        
        return results

    def _process_headlines(self, items):
        """
        处理头条新闻：硬排除 → 混合分类（规则+LLM）→ 筛选出指定类别的新闻
        """
        result = []
        uncertain_items = []  # 需要 LLM 判断的
        uncertain_indices = []  # 记录原始索引
        
        for item in items:
            # 1. 硬排除
            if self._is_hard_excluded(item):
                continue
            
            # 2. 规则分类（带置信度）
            predicted_category, confidence = self._classify_item(item)
            
            # 3. 根据置信度决定是否需要 LLM
            if confidence >= 0.75:  # 规则很确定
                if predicted_category == self.category:
                    result.append(item)
            else:  # 不确定，交给 LLM
                uncertain_items.append(item)
                uncertain_indices.append(len(result) + len(uncertain_items) - 1)
        
        # 4. LLM 批量处理不确定的
        if uncertain_items:
            logger.info(f"规则分类: {len(result)} 条确定，{len(uncertain_items)} 条需要 LLM 判断")
            llm_results = self._batch_classify_with_llm(uncertain_items)
            
            for item, res in zip(uncertain_items, llm_results):
                if res['category'] == self.category and not res['is_noise']:
                    result.append(item)
            
            logger.info(f"LLM 分类后: 新增 {len(result) - len([i for i in items if not self._is_hard_excluded(i)]) + len(uncertain_items)} 条")
        
        return {
            "section": "headline",
            "items": result
        }


class ClassifyRussia(Classify):
    """
    俄罗斯新闻分类器
    用于处理包含俄罗斯新闻的分类逻辑，并进行关键词去噪音
    """

    # 噪音关键词黑名单（娱乐、体育、生活类）
    NOISE_KEYWORDS = [
        "horoscope", "astrology", "celebrity", "gossip", "recipe", "travel", "tourism",
        "fashion", "beauty", "quiz", "podcast", "movie", "film", "music", "tv", "show",
        "football", "hockey", "match", "tournament", "weather", "sport",
        "星座", "八卦", "明星", "娱乐", "美食", "菜谱", "旅游", "体育", "比赛", "天气",
        "гороскоп", "астрол", "рецеп", "путеше", "туризм", "спорт", "футбол", "хокке", "погода",
    ]

    def _is_noise(self, item):
        """判断是否为噪音内容（娱乐、体育、生活等）"""
        title = (item.get("title") or "").lower()
        summary = (item.get("summaryText") or "").lower()

        # 检查标题和摘要中是否包含噪音关键词
        text = f"{title} {summary}"
        return any(kw in text for kw in self.NOISE_KEYWORDS)

    def _classify_item(self, item):
        """
        根据俄罗斯新闻的特征进行分类
        
        Returns:
            tuple: (category, confidence) 类别和置信度(0-1)
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)

        # 特别处理俄罗斯新闻标签
        if "label/俄罗斯" in cats or "россия" in src:
            return "俄罗斯", 0.95

        # 如果新闻来自俄罗斯来源，或涉及俄罗斯相关事务
        russian_keywords = ["russia", "russian", "putin", "путин", "kremlin", "кремл", "moscow", "москв"]
        keyword_match = sum(1 for kw in russian_keywords if kw in title)
        
        if keyword_match >= 2:
            return "俄罗斯", 0.9
        elif keyword_match == 1:
            return "俄罗斯", 0.6

        # 调用父类的方法，如果新闻没涉及俄罗斯，按父类规则分类
        return super()._classify_item(item)

    def _process_headlines(self, items):
        """
        处理俄罗斯新闻：硬排除 → 混合分类（规则+LLM）→ 去噪音 → 筛选
        """
        result = []
        uncertain_items = []
        
        for item in items:
            # 1. 硬排除
            if self._is_hard_excluded(item):
                continue

            # 2. 规则分类（带置信度）
            predicted_category, confidence = self._classify_item(item)

            # 3. 根据置信度决定是否需要 LLM
            if confidence >= 0.75:
                # 规则很确定
                if predicted_category == self.category:
                    # 4. 去噪音：过滤掉娱乐、体育等内容
                    if not self._is_noise(item):
                        result.append(item)
            else:
                # 不确定，交给 LLM
                uncertain_items.append(item)

        # 5. LLM 批量处理不确定的
        if uncertain_items:
            logger.info(f"俄罗斯新闻 - 规则分类: {len(result)} 条确定，{len(uncertain_items)} 条需要 LLM 判断")
            llm_results = self._batch_classify_with_llm(uncertain_items)
            
            for item, res in zip(uncertain_items, llm_results):
                if res['category'] == self.category and not res['is_noise']:
                    result.append(item)

        return {
            "section": "headline",
            "items": result
        }
