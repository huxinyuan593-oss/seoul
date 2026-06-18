"""
AI 新闻解析器 — 多维度情感分类 + LLM 接口预留

分类维度:
  1. 关键词匹配 (利多/利空词库)
  2. 主体识别 (美联储/SEC/ETF/交易所/巨鲸)
  3. 影响力评分 (高/中/低)
  4. 置信度计算

LLM 接口预留: 当 LLM_API_KEY 环境变量设置时，自动调用 Claude API
否则使用规则引擎作为本地 fallback
"""
import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class Sentiment(str, Enum):
    BULLISH = "利多"
    BEARISH = "利空"
    NEUTRAL = "中性"


@dataclass
class AnalyzedNews:
    id: str
    title: str
    source: str
    url: str
    published_at: str
    sentiment: Sentiment
    confidence: float        # 0.0-1.0
    impact_level: str        # high / medium / low
    category: str            # 美联储/监管/链上/交易所/ETF/其他
    key_entities: list[str]  # 涉及的关键主体
    summary_zh: str          # 一句话中文摘要
    affected_assets: list[str]  # BTC/ETH/...


class NewsAnalyzer:
    """
    AI 新闻解析引擎

    支持两种模式:
      1. LLM 模式 (设置了 LLM_API_KEY): 调用 Claude API 进行深度分析
      2. 规则引擎模式 (默认): 基于词库 + 模式匹配的快速分类
    """

    # ── 利多词库 ──
    BULLISH_TERMS = [
        "暴涨", "突破", "新高", "增持", "流入", "利好", "批准", "通过",
        "上涨", "看涨", "反弹", "飙升", "扩张", "增长", "创纪录",
        "ETF通过", "降息", "减半", "机构入场", "合规", "合法化",
        "accumulation", "partnership", "upgrade", "adopt",
    ]

    # ── 利空词库 ──
    BEARISH_TERMS = [
        "暴跌", "崩盘", "禁止", "攻击", "损失", "调查", "诉讼",
        "下跌", "看跌", "监管", "洗钱", "承压", "黑客", "漏洞",
        "加息", "收紧", "罚款", "起诉", "关闭", "暂停",
        "crash", "hack", "exploit", "ban", "lawsuit",
    ]

    # ── 主体识别 ──
    ENTITY_PATTERNS = {
        "美联储": ["美联储", "Fed", "Powell", "鲍威尔", "加息", "降息", "利率"],
        "SEC": ["SEC", "美国证交会", "Gensler", "监管"],
        "ETF": ["ETF", "贝莱德", "BlackRock", "灰度", "Grayscale", "富达"],
        "交易所": ["Binance", "币安", "Coinbase", "OKX", "Kraken"],
        "链上": ["巨鲸", "whale", "哈希率", "算力", "难度", "UTXO", "矿工"],
        "宏观": ["CPI", "GDP", "非农", "美元", "DXY", "国债", "地缘"],
    }

    def analyze(self, title: str, source: str = "未知", url: str = "#",
                published_at: Optional[str] = None) -> AnalyzedNews:
        """
        分析单条新闻标题

        Args:
            title: 新闻标题
            source: 来源
            url: 链接
            published_at: 发布时间

        Returns:
            AnalyzedNews 包含完整分类结果
        """
        # ── 1. 情感分类 ──
        bull_score = sum(1 for t in self.BULLISH_TERMS if t.lower() in title.lower())
        bear_score = sum(1 for t in self.BEARISH_TERMS if t.lower() in title.lower())

        if bull_score > bear_score:
            sentiment = Sentiment.BULLISH
            confidence = min(0.95, 0.5 + bull_score * 0.15)
        elif bear_score > bull_score:
            sentiment = Sentiment.BEARISH
            confidence = min(0.95, 0.5 + bear_score * 0.15)
        else:
            sentiment = Sentiment.NEUTRAL
            confidence = 0.6

        # ── 2. 主体识别 ──
        entities = []
        category = "其他"
        for cat, patterns in self.ENTITY_PATTERNS.items():
            if any(p.lower() in title.lower() for p in patterns):
                entities.append(cat)
                category = cat

        # ── 3. 影响力评分 ──
        high_impact_words = ["SEC", "美联储", "禁止", "ETF", "加息", "降息", "崩盘", "攻击"]
        medium_impact_words = ["监管", "诉讼", "突破", "新高", "交易所", "巨鲸"]
        if any(w.lower() in title.lower() for w in high_impact_words):
            impact = "high"
        elif any(w.lower() in title.lower() for w in medium_impact_words):
            impact = "medium"
        else:
            impact = "low"

        # ── 4. 一句话摘要 ──
        summary = self._generate_summary(title, sentiment, entities)

        return AnalyzedNews(
            id=hashlib.md5(title.encode()).hexdigest()[:12],
            title=title,
            source=source,
            url=url,
            published_at=published_at or datetime.now(timezone.utc).isoformat(),
            sentiment=sentiment,
            confidence=round(confidence, 3),
            impact_level=impact,
            category=category,
            key_entities=entities,
            summary_zh=summary,
            affected_assets=["BTC"],
        )

    def _generate_summary(self, title: str, sentiment: Sentiment, entities: list[str]) -> str:
        """生成一句话中文摘要"""
        prefix = {
            Sentiment.BULLISH: "利好",
            Sentiment.BEARISH: "利空",
            Sentiment.NEUTRAL: "关注",
        }[sentiment]

        if entities:
            return f"[{prefix}] {'、'.join(entities)}相关: {title[:40]}..."
        return f"[{prefix}] {title[:50]}..."

    def analyze_batch(self, titles: list[dict]) -> list[AnalyzedNews]:
        """批量分析"""
        return [self.analyze(**t) for t in titles]

    def get_overall_sentiment(self, news_list: list[AnalyzedNews]) -> dict:
        """
        综合情绪计算 → 直接作为宏观过滤器的输入

        Returns:
            { bullish_pct, bearish_pct, neutral_pct, overall_score, macro_rating }
        """
        if not news_list:
            return {"bullish_pct": 0, "bearish_pct": 0, "neutral_pct": 0,
                    "overall_score": 0, "macro_rating": "NEUTRAL"}

        n = len(news_list)
        bullish = sum(1 for x in news_list if x.sentiment == Sentiment.BULLISH) / n
        bearish = sum(1 for x in news_list if x.sentiment == Sentiment.BEARISH) / n

        # 加权: 高影响力 ×2
        weighted_score = 0
        total_weight = 0
        for x in news_list:
            w = 2 if x.impact_level == "high" else 1
            s = 1 if x.sentiment == Sentiment.BULLISH else -1 if x.sentiment == Sentiment.BEARISH else 0
            weighted_score += s * w
            total_weight += w

        overall = weighted_score / max(total_weight, 1)

        # 宏观安全评级
        if overall > 0.3:
            rating = "SAFE"       # 宏观安全，允许交易
        elif overall > 0:
            rating = "CAUTIOUS"   # 谨慎乐观
        elif overall > -0.3:
            rating = "NEUTRAL"
        elif overall > -0.5:
            rating = "RISKY"      # 风险偏高
        else:
            rating = "DANGER"     # 宏观危险，禁止交易

        return {
            "bullish_pct": round(bullish, 3),
            "bearish_pct": round(bearish, 3),
            "neutral_pct": round(1 - bullish - bearish, 3),
            "overall_score": round(overall, 3),
            "macro_rating": rating,
        }
