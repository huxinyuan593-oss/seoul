import { useState, useEffect } from 'react';

interface NewsItem {
  id: string; title: string; url: string; source: string;
  publishedAt: string; sentiment: string; sentimentScore: number;
  impact: string;
}

interface NewsData {
  news: NewsItem[];
  sentiment: { bullish: number; bearish: number; neutral: number; overall: number };
}

export function NewsPanel() {
  const [data, setData] = useState<NewsData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchNews = async () => {
    try {
      const res = await fetch('http://localhost:8081/news');
      const json: NewsData = await res.json();
      setData(json);
    } catch {
      // Use demo data
      setData(null);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchNews();
    const interval = setInterval(fetchNews, 60000);
    return () => clearInterval(interval);
  }, []);

  // ── WebSocket fallback ──
  useEffect(() => {
    try {
      const ws = new WebSocket('ws://localhost:8080');
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'news') setData(msg.data);
        } catch {}
      };
      return () => ws.close();
    } catch { return; }
  }, []);

  if (loading) return <div className="panel"><div className="panel-title">📰 市场消息</div><div className="empty">加载中...</div></div>;

  const s = data?.sentiment;
  const overallPct = s ? Math.round((s.overall + 1) / 2 * 100) : 50;

  return (
    <div className="news-panel">
      {/* Sentiment Bar */}
      {s && (
        <div className="news-sentiment-bar">
          <div className="ns-gauge">
            <div className="ns-gauge-label">
              <span>😱 恐慌</span>
              <span>市场情绪指数</span>
              <span>😤 贪婪</span>
            </div>
            <div className="ns-gauge-track">
              <div className="ns-gauge-fill" style={{ width: `${overallPct}%` }} />
              <div className="ns-gauge-marker" style={{ left: `${overallPct}%` }}>
                {overallPct > 65 ? '🟢' : overallPct > 45 ? '🟡' : '🔴'}
              </div>
            </div>
            <div className="ns-gauge-stats">
              <span style={{color:'#3fb950'}}>🟢 利好 {Math.round(s.bullish * 100)}%</span>
              <span style={{color:'#8b949e'}}>⚪ 中性 {Math.round(s.neutral * 100)}%</span>
              <span style={{color:'#f85149'}}>🔴 利空 {Math.round(s.bearish * 100)}%</span>
            </div>
          </div>
        </div>
      )}

      {/* News List */}
      <div className="ns-list">
        {(data?.news || []).map((item) => (
          <div key={item.id} className={`ns-item impact-${item.impact}`}>
            <div className="ns-item-header">
              <span className={`ns-sentiment sentiment-${item.sentiment}`}>
                {item.sentiment === 'positive' ? '📈' : item.sentiment === 'negative' ? '📉' : '➖'}
              </span>
              <span className="ns-source">{item.source}</span>
              {item.impact === 'high' && <span className="ns-impact-high">⚡重磅</span>}
              <span className="ns-time">{formatTime(item.publishedAt)}</span>
            </div>
            <div className="ns-title">{item.title}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return '刚刚';
  if (mins < 60) return `${mins}分钟前`;
  const hours = Math.floor(mins / 60);
  return `${hours}小时前`;
}
