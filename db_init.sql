-- FinanceOS — Database Initialisation Script

CREATE DATABASE IF NOT EXISTS finance_db;
USE finance_db;

-- ── Users Table ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    email      VARCHAR(150)  NOT NULL UNIQUE,
    password   VARCHAR(255)  NOT NULL,
    role       ENUM('admin','analyst','viewer') NOT NULL DEFAULT 'viewer',
    status     ENUM('active','inactive')        NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Records Table ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS records (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT            NOT NULL,
    amount      DECIMAL(12,2)  NOT NULL,
    type        ENUM('income','expense') NOT NULL,
    category    VARCHAR(100)   NOT NULL,
    date        DATE           NOT NULL,
    description TEXT,
    status      ENUM('active','deleted') NOT NULL DEFAULT 'active',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_user_id  (user_id),
    INDEX idx_date     (date),
    INDEX idx_type     (type),
    INDEX idx_category (category),
    INDEX idx_status   (status)
);

-- ── Audit Logs Table ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT          NOT NULL,
    action     VARCHAR(100) NOT NULL,
    detail     TEXT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_time (created_at)
);

-- ── Seed: Initial Admin User ───────────────────────────────────
INSERT IGNORE INTO users (name, email, password, role, status)
VALUES (
    'Super Admin',
    'admin@finance.com',
    '$2b$12$R5yqcgAEI884dN4o.h75FO57JShyUXy2K5H1Vqeca8HABfpFttiFi',
    'admin',
    'active'
);