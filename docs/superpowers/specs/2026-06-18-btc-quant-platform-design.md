# BTC 量化交易平台 — 系统设计文档

> **状态：** 已批准 · **日期：** 2026-06-18 · **角色：** 首席区块链架构师 & 量化金融工程专家

## 1. 项目概述

构建金融级 BTC 量化交易平台，底层融合 8 大区块链技术，应用层集成 8 大量化模型。核心原则：**策略与执行物理隔离**，量化引擎不触碰私钥。

## 2. 系统架构

### 2.1 5 大子系统

| 子系统 | 语言 | 职责 |
|--------|------|------|
| 📡 行情接入层 | TypeScript/Node.js | WebSocket 实时推送 OHLCV，TradingView DataFeed 适配，ClickHouse 持久化，延迟 < 50ms |
| ⚡ 撮合引擎层 | TypeScript | 内存 Order Book，高并发撮合，UTXO 映射锁定，幂等性校验，Redis 分布式锁 |
| 🧠 量化决策引擎 | Python | 独立服务，8 大量化模型计算，熔断控制，信号生成 |
| 🔐 业务审计层 | Python | PostgreSQL 交易流水，Merkle Tree 路径验证，BTC OP_RETURN 链上锚定，防篡改校验 |
| 📊 高性能前端 | React/TypeScript | TradingView K线，下单面板，量化策略配置，回测控制台，审计查询 |

### 2.2 数据流

```
BTC Full Node → 行情网关(多源聚合) → Redis(实时缓存) → 量化引擎(读行情)
                                         │                    │
                                    ClickHouse           TradeSignal
                                    (历史K线)            (RequestID)
                                         │                    │
                                    回测引擎 ←───────────────┘
                                         │                    ▼
                                    绩效报告            Order Service
                                                       → UTXO锁定
                                                       → ECDSA签名
                                                       → 广播BTC交易
                                                       → PostgreSQL流水
                                                       → Merkle Engine
                                                       → OP_RETURN锚定
```

### 2.3 量化引擎内部架构

```
数据输入层 (Redis Pub/Sub) → 特征工程
    ↓
8大量化模型 (独立模块):
  ① GBM 几何布朗运动     ② BSM 期权定价
  ③ Mean-Variance 优化   ④ GARCH 波动率预测
  ⑤ Z-Score 统计套利     ⑥ HMM 市场状态识别
  ⑦ PCA 主成分降维       ⑧ Kelly 最优仓位
    ↓
熔断控制器 (GARCH σ² 超阈值 → 禁止下单)
    ↓
信号生成器 (TradeSignal + RequestID UUIDv7 + 幂等性标识)
    ↓
REST API → 执行层
```

### 2.4 离线回测引擎

```
DataLoader (从ClickHouse加载历史OHLCV)
    ↓
事件驱动循环 (逐K线回放)
    ↓ 每根K线:
    特征计算 → 8大模型运算 → 信号生成 → 模拟成交
    (滑点: N(0, 0.01%), 冲击: 0.001% × √size)
    ↓
MetricsEngine 输出:
  • 胜率 (Win Rate)         阈值: > 45% 合格, > 55% 优秀
  • 夏普比率 (Sharpe Ratio)  阈值: > 1.0 合格, > 2.0 优秀
  • 最大回撤 (Max Drawdown)  阈值: < 20% 合格, < 10% 优秀
  • 卡尔玛比率 (Calmar)      阈值: > 0.5 合格, > 1.0 优秀
  • 索提诺比率 (Sortino)     阈值: > 1.5 合格, > 3.0 优秀
  • 盈亏比 (Profit Factor)   阈值: > 1.5 合格, > 2.0 优秀
```

## 3. 关键技术设计

### 3.1 策略与执行隔离

- 量化引擎与执行层通过 REST API 通信
- 量化引擎**不持有私钥**，不直接操作 UTXO
- 策略 BUG → 底层 UTXO 校验自动拦截双花
- 量化引擎可独立部署、独立扩缩容、热更新策略参数

### 3.2 幂等性 + UTXO 分布式锁

- **幂等性锁**：`Redis SET NX idempotency:{client}:{key} EX 300` — 防止网络重试导致重复下单
- **UTXO 锁**：Lua 原子脚本 `all-or-nothing` 锁定所有输入 UTXO，TTL 2 小时
- **释放**：仅锁持有者可释放（防误删）

### 3.3 事务状态机 (14 步)

SIGNAL → FUSE → IDEM → UTXO → ORDER → SIGNED → BROADCAST → AWAIT → CONFIRMED → MERKLE → ANCHORED

- 毫秒级：Signaling → 签名 (乐观执行)
- 分钟级：等待 BTC 确认 (异步，不阻塞)
- 终态：Merkle Root 写入 OP_RETURN，永久不可篡改

### 3.4 RequestID 全链路审计

RequestID (UUIDv7, 时间有序) 贯穿：
信号产生 → 熔断检查 → 幂等校验 → UTXO锁定 → 订单入库 → 链上签名 → 确认监听 → Merkle存证

### 3.5 回测→实盘闭环

回测 → 参数网格搜索/贝叶斯优化 → 纸上交易(Paper Trading) → 小仓位启动 → 逐步放大 → 持续监控偏离警报

## 4. BTC 接口抽象

```python
class IBitcoinClient(ABC):
    """支持 Mainnet / Testnet3 / Regtest 三种模式"""
    async def get_block_hash(self, height: int) -> str: ...
    async def get_block(self, hash: str) -> Block: ...
    async def send_raw_transaction(self, hex_tx: str) -> str: ...
    async def get_network_info(self) -> NetworkInfo: ...
    async def get_tx_out(self, txid: str, vout: int) -> UTXO | None: ...
```

## 5. 8 大区块链技术落地位置

| 技术 | 落地位置 |
|------|----------|
| ① 分布式账本 | Bitcoin Full Node — 每个节点维护完整账本副本 |
| ② 非对称加密 | ECDSA secp256k1 — 私钥签名交易，量化引擎不碰私钥 |
| ③ 哈希防篡改 | 双 SHA-256 Merkle Tree — 任何数据修改都会改变 Root |
| ④ 链式结构 | 区块通过 prev_block_hash 串联，修改需重算所有后续 |
| ⑤ 共识机制 | PoW 工作量证明，~10 分钟出块，6 确认不可逆 |
| ⑥ 智能合约 | BTC Script — OP_RETURN 存储 Merkle Root |
| ⑦ P2P 网络 | 交易广播至 ~10,000 节点，Block Monitor 异步监听 |
| ⑧ 默克尔路径验证 | MerkleProof{siblings[], index} — 独立验证任意交易 |

## 6. 目录结构

```
btc-quant-platform/
├── market-data/            # 📡 行情接入层 (TypeScript)
├── matching-engine/        # ⚡ 撮合引擎层 (TypeScript)
├── quant-engine/           # 🧠 量化决策引擎 (Python)
│   ├── models/             # 8大量化模型
│   ├── backtesting/        # 离线回测引擎
│   └── api/                # REST API (FastAPI)
├── audit-layer/            # 🔐 业务审计层 (Python)
│   ├── core/
│   │   ├── transaction_store.py
│   │   ├── merkle_engine.py
│   │   ├── chain_anchor.py
│   │   └── audit_verifier.py
│   ├── btc/
│   │   ├── interface.py    # IBitcoinClient
│   │   ├── mainnet_client.py
│   │   ├── testnet_client.py
│   │   └── regtest_client.py
│   ├── workers/
│   │   ├── block_monitor.py
│   │   ├── merkle_aggregator.py
│   │   └── anchor_worker.py
│   └── api/
├── frontend/               # 📊 高性能前端 (React/TS)
├── docker-compose.yml      # PostgreSQL + Redis + ClickHouse + BTC Node
└── docs/superpowers/
    ├── specs/
    └── plans/
```

## 7. 开发迭代路径

按子系统优先级逐个深入：

1. **🔐 业务审计层** (已选定为首个子系统)
2. 🧠 量化决策引擎 + 回测引擎
3. 📡 行情接入层
4. ⚡ 撮合引擎层
5. 📊 高性能前端

每个子系统经历独立循环：`spec → plan → subagent-driven-development → review → finish`
