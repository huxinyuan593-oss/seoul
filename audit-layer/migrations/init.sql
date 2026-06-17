-- BTC Audit Layer — Database Schema

CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(36) UNIQUE NOT NULL,
    btc_txid VARCHAR(64),
    side VARCHAR(4) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    size DOUBLE PRECISION NOT NULL,
    total_value DOUBLE PRECISION NOT NULL,
    fee DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'PENDING',
    confirmations INTEGER DEFAULT 0,
    utxo_locks TEXT,
    raw_tx_hex TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_request_id ON transactions(request_id);
CREATE INDEX IF NOT EXISTS idx_transactions_btc_txid ON transactions(btc_txid);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);

CREATE TABLE IF NOT EXISTS anchor_records (
    id SERIAL PRIMARY KEY,
    batch_date DATE UNIQUE NOT NULL,
    merkle_root VARCHAR(64) NOT NULL,
    transaction_count INTEGER NOT NULL,
    btc_txid VARCHAR(64),
    block_height INTEGER,
    block_hash VARCHAR(64),
    confirmations INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anchor_records_date ON anchor_records(batch_date);
CREATE INDEX IF NOT EXISTS idx_anchor_records_btc_txid ON anchor_records(btc_txid);
