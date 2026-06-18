"""
每日行情摘要引擎 — 盘后分析 + 次日趋势预测 + UTC 00:00 自动归档

生成逻辑:
  1. 收集当日所有已分析新闻
  2. 按类别聚合 (美联储/监管/链上/交易所/ETF)
  3. 提取核心驱动因素 (出现频率最高 + 影响力最大)
  4. 综合情绪 → 次日趋势预测
  5. 生成结构化摘要文本
  6. 归档到 /data/summaries/ 供审计回溯
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from src.ai_analyst.news_analyzer import AnalyzedNews, Sentiment, NewsAnalyzer


@dataclass
class DailySummary:
    date: str                          # YYYY-MM-DD
    generated_at: str                  # ISO timestamp
    total_news_count: int
    sentiment_distribution: dict       # {bullish, bearish, neutral}
    core_drivers: list[dict]           # [{factor, sentiment, impact, detail}]
    category_breakdown: dict           # {category: {count, sentiment}}
    market_narrative: str              # AI生成的当日市场叙事
    next_day_outlook: str              # 次日趋势预测
    macro_safety_rating: str           # SAFE/CAUTIOUS/NEUTRAL/RISKY/DANGER
    key_events: list[str]              # 今日关键事件列表
    archive_path: str = ""             # 归档文件路径


class DailySummaryEngine:
    """
    每日行情摘要引擎

    自动在 UTC 00:00 触发生成，也可手动调用。
    所有摘要归档到 data/summaries/ 目录，文件名: YYYY-MM-DD.json
    """

    ARCHIVE_DIR = "data/summaries"

    def __init__(self, archive_dir: Optional[str] = None):
        self.analyzer = NewsAnalyzer()
        self.archive_dir = archive_dir or self.ARCHIVE_DIR
        os.makedirs(self.archive_dir, exist_ok=True)

    def generate(self, analyzed_news: list[AnalyzedNews],
                 extra_context: Optional[dict] = None) -> DailySummary:
        """
        生成每日行情摘要

        Args:
            analyzed_news: 当日已分析的所有新闻
            extra_context: 额外上下文 (价格变动、波动率等)

        Returns:
            DailySummary 完整摘要对象
        """
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # ── 1. 情绪分布 ──
        sentiment = self.analyzer.get_overall_sentiment(analyzed_news)

        # ── 2. 按类别聚合 ──
        categories: dict[str, dict] = {}
        for news in analyzed_news:
            cat = news.category
            if cat not in categories:
                categories[cat] = {"count": 0, "bullish": 0, "bearish": 0, "neutral": 0, "items": []}
            categories[cat]["count"] += 1
            if news.sentiment == Sentiment.BULLISH:
                categories[cat]["bullish"] += 1
            elif news.sentiment == Sentiment.BEARISH:
                categories[cat]["bearish"] += 1
            else:
                categories[cat]["neutral"] += 1
            categories[cat]["items"].append(news.title[:60])

        # ── 3. 核心驱动因素 ──
        # 按影响力排序：high > medium > low
        impact_order = {"high": 3, "medium": 2, "low": 1}
        sorted_news = sorted(analyzed_news, key=lambda x: impact_order.get(x.impact_level, 0), reverse=True)
        core_drivers = []
        seen_cats = set()
        for news in sorted_news[:5]:
            if news.category not in seen_cats or news.impact_level == "high":
                core_drivers.append({
                    "factor": news.category,
                    "sentiment": news.sentiment.value,
                    "impact": news.impact_level,
                    "detail": news.summary_zh,
                })
                seen_cats.add(news.category)

        # ── 4. 关键事件 ──
        key_events = [
            n.title for n in sorted_news
            if n.impact_level == "high"
        ][:5]

        # ── 5. AI 叙事生成 ──
        narrative = self._generate_narrative(
            analyzed_news, sentiment, categories, extra_context
        )

        # ── 6. 次日展望 ──
        outlook = self._generate_outlook(sentiment, core_drivers)

        # ── 7. 宏观评级 ──
        rating = sentiment["macro_rating"]

        summary = DailySummary(
            date=today,
            generated_at=now.isoformat(),
            total_news_count=len(analyzed_news),
            sentiment_distribution=sentiment,
            core_drivers=core_drivers,
            category_breakdown={k: {"count": v["count"], "sentiment": self._dominant_sentiment(v)} for k, v in categories.items()},
            market_narrative=narrative,
            next_day_outlook=outlook,
            macro_safety_rating=rating,
            key_events=key_events,
        )

        # ── 8. 归档 ──
        summary.archive_path = self._archive(summary)

        return summary

    def load_summary(self, date_str: str) -> Optional[DailySummary]:
        """加载历史摘要"""
        path = os.path.join(self.archive_dir, f"{date_str}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return DailySummary(**data)

    def list_summaries(self, days: int = 30) -> list[str]:
        """列出最近N天的摘要日期"""
        files = sorted(os.listdir(self.archive_dir), reverse=True)
        return [f.replace(".json", "") for f in files if f.endswith(".json")][:days]

    # ── Private ──────────────────────────────────────────

    def _dominant_sentiment(self, cat_data: dict) -> str:
        b, e, n = cat_data["bullish"], cat_data["bearish"], cat_data["neutral"]
        if b > e and b > n:
            return "利多"
        elif e > b and e > n:
            return "利空"
        return "中性"

    def _generate_narrative(self, news: list[AnalyzedNews], sentiment: dict,
                            categories: dict, ctx: Optional[dict]) -> str:
        """生成当日市场叙事"""
        n = len(news)
        score = sentiment["overall_score"]

        if score > 0.3:
            tone = "整体偏向乐观"
        elif score > 0:
            tone = "谨慎偏乐观"
        elif score > -0.3:
            tone = "情绪中性"
        elif score > -0.5:
            tone = "风险情绪上升"
        else:
            tone = "市场恐慌情绪蔓延"

        cat_summary = "、".join(
            f"{cat}({data['count']}条)" for cat, data in sorted(categories.items(), key=lambda x: -x[1]["count"])[:4]
        )

        narrative = (
            f"【{tone}】今日共监测到 {n} 条相关资讯。"
            f"主要关注领域: {cat_summary}。"
        )

        # 添加价格背景
        if ctx:
            price = ctx.get("current_price", 0)
            change = ctx.get("daily_change_pct", 0)
            if price > 0:
                narrative += f" BTC现价 ${price:,.0f}，日内变动 {change:+.2f}%。"

        return narrative

    def _generate_outlook(self, sentiment: dict, drivers: list[dict]) -> str:
        """生成次日趋势预测"""
        score = sentiment["overall_score"]
        bullish_pct = sentiment["bullish_pct"]
        bearish_pct = sentiment["bearish_pct"]

        # 驱动因素提取
        bull_drivers = [d["factor"] for d in drivers if d["sentiment"] == "利多"]
        bear_drivers = [d["factor"] for d in drivers if d["sentiment"] == "利空"]

        outlook_parts = []

        if score > 0.3:
            outlook_parts.append("预计明日维持偏强震荡，")
            if bull_drivers:
                outlook_parts.append(f"利好因素({', '.join(bull_drivers)})可能继续发酵。")
        elif score > 0:
            outlook_parts.append("预计明日窄幅震荡，方向不明。")
        elif score > -0.3:
            outlook_parts.append("需关注明日开盘情绪变化，")
            if bear_drivers:
                outlook_parts.append(f"警惕{', '.join(bear_drivers)}方面的进一步发展。")
        elif score > -0.5:
            outlook_parts.append("预计明日承压，")
            if bear_drivers:
                outlook_parts.append(f"{', '.join(bear_drivers)}因素可能继续施压。")
        else:
            outlook_parts.append("⚠️ 明日存在较大下行风险，建议降低仓位观望。")

        # 概率量化
        up_prob = int(bullish_pct * 100)
        outlook_parts.append(f" 上涨概率约{up_prob}%。")

        return "".join(outlook_parts)

    def _archive(self, summary: DailySummary) -> str:
        """归档摘要到JSON文件"""
        path = os.path.join(self.archive_dir, f"{summary.date}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary.__dict__, f, ensure_ascii=False, indent=2, default=str)
        return path
