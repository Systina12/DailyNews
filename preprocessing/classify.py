# preprocessing/classify.py

import os
import re
import math
from typing import Dict, List, Tuple, Optional
from llms.llms import LLMClient
from utils.logger import get_logger
from config import settings

logger = get_logger("classify")


class Classify:
    """
    新闻分类器
    流程：硬排除 → 分类（头条需额外检查软内容）→ 筛选
    支持6个类别：头条、政治、军事、财经、科技、国际
    """

    def __init__(self, category):
        """
        Args:
            category: 要提取的类别（头条/政治/军事/财经/科技/国际）
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
        将新闻分类到6个类别之一
        分类优先级：头条 > 政治 > 军事 > 财经 > 科技 > 国际
        
        注意：俄罗斯新闻已在 filter_ru 中过滤，这里按内容正常分类
        
        Returns:
            tuple: (category, confidence) 类别和置信度(0-1)
        """
        title = (item.get("title") or "").lower()
        src = (item.get("origin", {}).get("title") or "").lower()
        categories = item.get("categories", [])
        cats = " ".join(str(c).lower() for c in categories)
        
        # 获取摘要用于辅助判断
        summary = (item.get("summaryText") or "")[:200].lower()
        full_text = f"{title} {summary}"

        # 1. 头条：来源标记为top 且 不是软内容
        if ("top" in src or "top" in cats or "头条" in src or "头条" in cats):
            if not self._is_soft_content(item):
                return "头条", 0.9  # 高置信度
            else:
                return "头条", 0.5  # 软内容降低置信度

        # 2. 政治
        political_keywords = [
            "election", "vote", "parliament", "government", "president", "prime minister",
            "policy", "sanction", "cabinet", "congress", "senate", "politic", "minister",
            "law", "legislation", "treaty", "diplomat", "kremlin", "putin",
            "选举", "政府", "总统", "议会", "内阁", "制裁", "部长", "法律", "立法", "普京", "克里姆林宫",
        ]
        political_sources = ["politics", "politica", "政治"]
        
        keyword_match = sum(1 for kw in political_keywords if kw in full_text)
        source_match = any(s in src for s in political_sources)
        
        if source_match:
            return "政治", 0.9  # 来源明确，高置信度
        elif keyword_match >= 3:
            return "政治", 0.85  # 多个关键词
        elif keyword_match == 2:
            return "政治", 0.75  # 两个关键词，刚好达到阈值
        elif keyword_match == 1:
            return "政治", 0.6  # 单个关键词，置信度中等

        # 3. 军事
        military_keywords = [
            "military", "war", "army", "navy", "air force", "defense", "weapon", "missile",
            "attack", "strike", "combat", "soldier", "troop", "battle", "conflict",
            "nato", "pentagon", "drone", "fighter", "tank", "submarine", "aircraft carrier",
            "nuclear", "bomb", "explosion", "warfare", "invasion", "occupation",
            "军事", "战争", "军队", "海军", "空军", "国防", "武器", "导弹",
            "攻击", "袭击", "战斗", "士兵", "部队", "冲突", "北约", "无人机", "战机", "坦克", "潜艇", "航母",
            "核武器", "炸弹", "爆炸", "入侵", "占领",
        ]
        military_sources = ["military", "defense", "guerra", "军事", "国防"]
        
        keyword_match = sum(1 for kw in military_keywords if kw in full_text)
        source_match = any(s in src for s in military_sources)
        
        if source_match:
            return "军事", 0.9  # 来源明确，高置信度
        elif keyword_match >= 3:
            return "军事", 0.85  # 多个关键词
        elif keyword_match == 2:
            return "军事", 0.75  # 两个关键词
        elif keyword_match == 1:
            return "军事", 0.6  # 单个关键词

        # 4. 财经
        econ_keywords = [
            "economy", "economic", "market", "stock", "inflation", "bank", "finance", "business",
            "trade", "tariff", "gdp", "debt", "bond", "currency", "dollar", "euro", "oil", "gas", "energy",
            "economia", "borsa", "mercato", "finanza",
            "经济", "股市", "通胀", "银行", "贸易", "关税", "债务", "货币", "石油", "天然气", "能源",
        ]
        econ_sources = ["business", "economia", "finance", "财经", "经济"]
        
        keyword_match = sum(1 for kw in econ_keywords if kw in full_text)
        source_match = any(s in src for s in econ_sources)
        
        if source_match:
            return "财经", 0.9
        elif keyword_match >= 3:
            return "财经", 0.85
        elif keyword_match == 2:
            return "财经", 0.75
        elif keyword_match == 1:
            return "财经", 0.6

        # 5. 科技
        tech_keywords = [
            "tech", "technology", "ai", "artificial intelligence", "software", "chip",
            "science", "research", "innovation", "startup", "app", "digital",
            "computer", "internet", "cyber", "data", "algorithm",
            "scienza", "tecnologia", "ricerca",
            "科技", "人工智能", "半导体", "软件", "芯片", "研究", "创新",
        ]
        tech_sources = ["tech", "science", "scienza", "technology", "科技"]
        
        keyword_match = sum(1 for kw in tech_keywords if kw in full_text)
        source_match = any(s in src for s in tech_sources)
        
        if source_match:
            return "科技", 0.9
        elif keyword_match >= 3:
            return "科技", 0.85
        elif keyword_match == 2:
            return "科技", 0.75
        elif keyword_match == 1:
            return "科技", 0.6

        # 6. 国际（兜底）
        return "国际", 0.4  # 兜底分类，置信度低

    def _batch_classify_with_llm(self, items: List[Dict]) -> List[Dict]:
        """
        使用 LLM 批量分类新闻
        
        Args:
            items: 待分类的新闻列表
            
        Returns:
            List[Dict]: 分类结果列表，每项包含 {'category': str, 'is_noise': bool}
        """
        if not items:
            return []
        
        llm_client = LLMClient()
        results = []
        
        # 使用配置的批次大小（Gemini 2.5 Flash Lite 支持 1M tokens 上下文）
        batch_size = settings.CLASSIFY_BATCH_SIZE
        
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

类别选项：头条/政治/军事/财经/科技/国际
是否噪音：yes（娱乐、体育、生活、文化类）/ no（政治、经济、科技、军事、国际新闻）

判断标准：
- 头条：重大突发事件、高层政治动态
- 政治：选举、政府、议会、政策、制裁
- 军事：战争、军队、武器、导弹、攻击、冲突
- 财经：经济、市场、股市、通胀、银行
- 科技：技术、AI、软件、芯片、科学
- 国际：其他国际新闻
- 噪音：娱乐、体育、旅游、美食、时尚、天气、星座

示例输出：
1|政治|no
2|军事|no
3|头条|yes
4|财经|no

请严格按照格式输出，每行一条："""
            
            try:
                logger.info(f"LLM 批量分类 {len(batch)} 条新闻（批次大小: {batch_size}）...")
                if settings.GROK_ONLY:
                    response = llm_client.request_grok(
                        prompt=prompt,
                        temperature=0.1,
                        max_tokens=500
                    )
                else:
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
            if confidence >= settings.CLASSIFY_CONFIDENCE_THRESHOLD:  # 使用配置的阈值
                if predicted_category == self.category:
                    result.append(item)
            else:  # 不确定，交给 LLM
                uncertain_items.append(item)
                uncertain_indices.append(len(result) + len(uncertain_items) - 1)
        
        # 4. LLM 批量处理不确定的
        if uncertain_items:
            logger.info(f"规则分类: {len(result)} 条确定，{len(uncertain_items)} 条需要 LLM 判断")
            before_llm = len(result)
            llm_results = self._batch_classify_with_llm(uncertain_items)
            
            for item, res in zip(uncertain_items, llm_results):
                if res['category'] == self.category and not res['is_noise']:
                    result.append(item)
            
            logger.info(f"LLM 分类后: 从 {len(uncertain_items)} 条中新增 {len(result) - before_llm} 条，总计 {len(result)} 条")
        else:
            logger.info(f"规则分类: {len(result)} 条确定，无需 LLM 判断")
        
        return {
            "section": "headline",
            "items": result
        }


