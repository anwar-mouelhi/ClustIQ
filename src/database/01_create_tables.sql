CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id VARCHAR(20) NOT NULL PRIMARY KEY,
    district_id VARCHAR(20),
    birth_date  DATE,
    gender      CHAR(1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_districts (
    district_id VARCHAR(20) NOT NULL PRIMARY KEY,
    region      VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_dispositions (
    disposition_id   VARCHAR(20) NOT NULL PRIMARY KEY,
    customer_id      VARCHAR(20) NOT NULL,
    account_id       VARCHAR(20) NOT NULL,
    disposition_type VARCHAR(20),
    INDEX idx_disp_customer (customer_id),
    INDEX idx_disp_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_accounts (
    account_id        VARCHAR(20) NOT NULL PRIMARY KEY,
    district_id       VARCHAR(20),
    account_type      VARCHAR(50),
    account_open_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_transactions (
    transaction_id     VARCHAR(20) NOT NULL PRIMARY KEY,
    account_id         VARCHAR(20) NOT NULL,
    transaction_date   DATE,
    transaction_amount DECIMAL(15,2),
    account_balance    DECIMAL(15,2),
    transaction_type   VARCHAR(50),
    INDEX idx_trans_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_loans (
    loan_id     VARCHAR(20) NOT NULL PRIMARY KEY,
    account_id  VARCHAR(20) NOT NULL,
    loan_date   DATE,
    loan_amount DECIMAL(15,2),
    loan_status VARCHAR(10),
    INDEX idx_loan_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_cards (
    card_id          VARCHAR(20) NOT NULL PRIMARY KEY,
    disposition_id   VARCHAR(20) NOT NULL,
    card_type        VARCHAR(20),
    card_issue_date  DATE,
    INDEX idx_card_disposition (disposition_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS stg_products (
    product_id                VARCHAR(20) NOT NULL PRIMARY KEY,
    account_id                VARCHAR(20) NOT NULL,
    product_type               VARCHAR(50),
    product_amount              DECIMAL(15,2),
    product_subscription_date  DATE,
    INDEX idx_product_account (account_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS customer_attributes (
    customer_id           VARCHAR(20) NOT NULL PRIMARY KEY,
    age_range             VARCHAR(10),
    gender                CHAR(1),
    region                VARCHAR(100),
    customer_category     VARCHAR(20),
    transaction_frequency INT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agg_loans (
    account_id  VARCHAR(20) NOT NULL PRIMARY KEY,
    loan_amount DECIMAL(15,2),
    loan_status VARCHAR(10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agg_cards (
    account_id VARCHAR(20) NOT NULL PRIMARY KEY,
    card_type  VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS agg_products (
    account_id                 VARCHAR(20) NOT NULL PRIMARY KEY,
    product_type               VARCHAR(50),
    product_subscription_date  DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
