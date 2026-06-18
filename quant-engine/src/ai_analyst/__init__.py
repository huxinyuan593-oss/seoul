"""
AI 内容分析引擎 — 每日行情动态解说与总结

Features:
  - 多源新闻抓取 (RSS/API fallback → 内置BTC新闻库)
  - AI 解析分类 (利多/利空/中性 + 置信度)
  - 每日盘后摘要 (核心驱动因素 + 次日趋势预测)
  - 宏观联动 (情绪倾向 → Resonance 宏观过滤器)
  - UTC 00:00 自动归档
"""
from .news_analyzer import NewsAnalyzer, AnalyzedNews, Sentiment
from .daily_summary import DailySummaryEngine, DailySummary
