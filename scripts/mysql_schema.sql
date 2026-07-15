-- MySQL storage schema for the Virtual Casino Simulator.
-- Apply this to a fresh database selected by CASINO_MYSQL_DATABASE before running with CASINO_STORAGE_PROVIDER=mysql.

-- Schema versions make provider bootstrap state explicit for restart and migration checks.
CREATE TABLE IF NOT EXISTS casino_schema_versions (
  component VARCHAR(64) PRIMARY KEY,
  schema_version VARCHAR(32) NOT NULL,
  applied_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Player wallets own fake-money balances and are locked during ledger settlement.
CREATE TABLE IF NOT EXISTS casino_players (
  player_id VARCHAR(64) PRIMARY KEY,
  display_name VARCHAR(255) NOT NULL,
  player_type VARCHAR(32) NOT NULL,
  balance DECIMAL(18,2) NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Ledger rows are append-only records of balance mutations.
CREATE TABLE IF NOT EXISTS casino_ledger (
  sequence_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ledger_id VARCHAR(64) NOT NULL UNIQUE,
  ts VARCHAR(64) NOT NULL,
  player_id VARCHAR(64) NOT NULL,
  game VARCHAR(64) NULL,
  round_id VARCHAR(128) NULL,
  transaction_type VARCHAR(128) NOT NULL,
  amount DECIMAL(18,2) NOT NULL,
  balance_before DECIMAL(18,2) NOT NULL,
  balance_after DECIMAL(18,2) NOT NULL,
  action_scope VARCHAR(64) NOT NULL DEFAULT '',
  action_key VARCHAR(191) NULL,
  action_fingerprint VARCHAR(128) NULL,
  details_json JSON NOT NULL,
  INDEX idx_casino_ledger_player_sequence (player_id, sequence_id),
  UNIQUE INDEX uq_casino_ledger_action (player_id, action_scope, action_key),
  CONSTRAINT fk_casino_ledger_player FOREIGN KEY (player_id) REFERENCES casino_players(player_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- History rows capture game outcome summaries used by casino and admin history APIs.
CREATE TABLE IF NOT EXISTS casino_history (
  sequence_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  timestamp VARCHAR(64) NOT NULL,
  game VARCHAR(64) NOT NULL,
  round_id VARCHAR(128) NOT NULL,
  player_id VARCHAR(64) NOT NULL,
  bet_type VARCHAR(128) NOT NULL,
  bet_label VARCHAR(255) NOT NULL,
  amount DECIMAL(18,2) NOT NULL,
  outcome VARCHAR(128) NOT NULL,
  payout DECIMAL(18,2) NOT NULL,
  balance_after DECIMAL(18,2) NOT NULL,
  details_json JSON NOT NULL,
  schema_version VARCHAR(32) NOT NULL,
  INDEX idx_casino_history_game_sequence (game, sequence_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Document rows hold small JSON settings payloads such as audio controls.
CREATE TABLE IF NOT EXISTS casino_documents (
  document_key VARCHAR(191) PRIMARY KEY,
  payload_json JSON NOT NULL,
  updated_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
