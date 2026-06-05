CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bank accounts (optional grouping for transactions)
CREATE TABLE IF NOT EXISTS bank_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name VARCHAR(255) NOT NULL,
    account_number VARCHAR(255),
    account_type VARCHAR(255),
    balance DECIMAL(12, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Imported / manual transactions
CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    bank_account_id UUID REFERENCES bank_accounts(id) ON DELETE CASCADE,
    amount DECIMAL(12, 2) NOT NULL,
    description VARCHAR(255) NOT NULL,
    category VARCHAR(255) DEFAULT 'Uncategorized',
    predicted_category VARCHAR(255) DEFAULT 'Uncategorized',
    transaction_type VARCHAR(10) NOT NULL DEFAULT 'expense', -- 'income' | 'expense'
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Category reference / palette (seeded with defaults below)
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    parent_category VARCHAR(100),
    color VARCHAR(7) DEFAULT '#007bff'
);

-- Monthly per-category budgets
CREATE TABLE IF NOT EXISTS budgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(255) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    month CHAR(7) NOT NULL, -- 'YYYY-MM'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, category, month)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON bank_transactions(user_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_category ON bank_transactions(category);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_user_id ON bank_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_user_id ON bank_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_budgets_user_month ON budgets(user_id, month);

-- Default categories with display colors
INSERT INTO categories (name, color) VALUES
    ('Groceries',     '#28a745'),
    ('Dining',        '#fd7e14'),
    ('Transport',     '#6f42c1'),
    ('Utilities',     '#20c997'),
    ('Rent',          '#dc3545'),
    ('Entertainment', '#e83e8c'),
    ('Shopping',      '#ffc107'),
    ('Health',        '#17a2b8'),
    ('Income',        '#198754'),
    ('Uncategorized', '#6c757d')
ON CONFLICT (name) DO NOTHING;
