/**
 * 行情动态栏 — 滚动快讯 + AI 每日摘要
 */
import { useState, useEffect, useRef } from 'react';

interface AnalyzedNews {
  id: string; title: string; source: string; sentiment: string;
  confidence: number; impactLevel: string; category: string; summaryZh: string;
}
interface DailySummaryData {
  date: string; marketNarrative: string; nextDayOutlook: string;
  macroSafetyRating: string; sentimentDistribution: Record<string,number>;
  coreDrivers: { factor: string; sentiment: string; impact: string; detail: string }[];
  keyEvents: string[]; totalNewsCount: number; categoryBreakdown: Record<string,{count:number;sentiment:string}>;
}

export function MarketTicker() {
  const [news, setNews] = useState<AnalyzedNews[]>([]);
  const [summary, setSummary] = useState<DailySummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const tickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8001/api/quant/daily-summary');
        const data = await res.json();
        setNews(data.analyzedNews || []);
        setSummary(data.summary);
      } catch {}
      setLoading(false);
    };
    fetchData();
  }, []);

  if (loading) return <div className="ticker-loading">加载行情动态...</div>;

  const ratingColors: Record<string, string> = {
    SAFE: 'var(--tv-green)', CAUTIOUS: '#d2991d', NEUTRAL: 'var(--tv-muted)',
    RISKY: 'var(--tv-orange)', DANGER: 'var(--tv-red)',
  };
  const ratingLabels: Record<string, string> = {
    SAFE: '🟢 安全', CAUTIOUS: '🟡 谨慎', NEUTRAL: '⚪ 中性',
    RISKY: '🟠 风险', DANGER: '🔴 危险',
  };

  return (
    <div className="market-ticker">
      {/* ── Scrolling News Ticker ── */}
      <div className="ticker-scroll" onMouseEnter={() => setExpanded(true)} onMouseLeave={() => setExpanded(false)}>
        <div className="ticker-track" ref={tickerRef}>
          {[...news, ...news].map((n, i) => (
            <span key={`${n.id}-${i}`} className={`ticker-item sentiment-${n.sentiment}`}>
              <span className="ticker-dot" style={{
                background: n.sentiment === '利多' ? 'var(--tv-green)' : n.sentiment === '利空' ? 'var(--tv-red)' : 'var(--tv-muted)'
              }} />
              {n.impactLevel === 'high' && '⚡'}
              {n.title}
              <span className="ticker-source">{n.source}</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Macro Safety Badge ── */}
      {summary && (
        <div className="ticker-macro-badge" style={{ borderColor: ratingColors[summary.macroSafetyRating] || 'var(--tv-muted)' }}>
          <span>AI宏观评级:</span>
          <strong style={{ color: ratingColors[summary.macroSafetyRating] || 'var(--tv-muted)' }}>
            {ratingLabels[summary.macroSafetyRating] || summary.macroSafetyRating}
          </strong>
          <span className="ticker-news-count">{summary.totalNewsCount}条资讯</span>
          <button className="ticker-expand-btn" onClick={() => setExpanded(!expanded)}>
            {expanded ? '收起 ▲' : '详情 ▼'}
          </button>
        </div>
      )}

      {/* ── Expanded: Daily Summary ── */}
      {expanded && summary && (
        <div className="ticker-detail">
          {/* Narrative */}
          <div className="td-section">
            <div className="td-title">📝 今日市场叙事</div>
            <div className="td-narrative">{summary.marketNarrative}</div>
          </div>

          {/* Outlook */}
          <div className="td-section">
            <div className="td-title">🔮 明日趋势预测</div>
            <div className="td-outlook">{summary.nextDayOutlook}</div>
          </div>

          {/* Core Drivers */}
          <div className="td-section">
            <div className="td-title">🎯 核心驱动因素</div>
            <div className="td-drivers">
              {summary.coreDrivers.map((d, i) => (
                <div key={i} className={`td-driver impact-${d.impact}`}>
                  <span className="td-driver-factor">{d.factor}</span>
                  <span className="td-driver-sentiment" style={{
                    color: d.sentiment === '利多' ? 'var(--tv-green)' : d.sentiment === '利空' ? 'var(--tv-red)' : 'var(--tv-muted)'
                  }}>{d.sentiment}</span>
                  <span className="td-driver-detail">{d.detail}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Sentiment Distribution */}
          <div className="td-section">
            <div className="td-title">📊 情绪分布</div>
            <div className="td-sentiment-bar">
              <div className="td-bar-seg bullish" style={{ width: `${summary.sentimentDistribution.bullish_pct * 100}%` }}>
                {summary.sentimentDistribution.bullish_pct > 0.15 && `利多 ${(summary.sentimentDistribution.bullish_pct * 100).toFixed(0)}%`}
              </div>
              <div className="td-bar-seg neutral" style={{ width: `${summary.sentimentDistribution.neutral_pct * 100}%` }}>
                {summary.sentimentDistribution.neutral_pct > 0.15 && `中性 ${(summary.sentimentDistribution.neutral_pct * 100).toFixed(0)}%`}
              </div>
              <div className="td-bar-seg bearish" style={{ width: `${summary.sentimentDistribution.bearish_pct * 100}%` }}>
                {summary.sentimentDistribution.bearish_pct > 0.15 && `利空 ${(summary.sentimentDistribution.bearish_pct * 100).toFixed(0)}%`}
              </div>
            </div>
          </div>

          {/* Key Events */}
          {summary.keyEvents.length > 0 && (
            <div className="td-section">
              <div className="td-title">⚡ 关键事件</div>
              {summary.keyEvents.map((e, i) => (
                <div key={i} className="td-key-event">{e}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
