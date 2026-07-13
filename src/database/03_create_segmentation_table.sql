CREATE TABLE IF NOT EXISTS customer_segments (
    customer_id             VARCHAR(20) NOT NULL PRIMARY KEY,
    segment                 INT NOT NULL,
    avg_transaction_amount  DECIMAL(15,2),
    transaction_frequency   INT,
    avg_account_balance     DECIMAL(15,2),
    nb_products             INT,
    account_age_days        INT,
    total_loan_amount       DECIMAL(15,2),
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_segment (segment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
