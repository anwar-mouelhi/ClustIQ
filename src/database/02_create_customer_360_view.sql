CREATE OR REPLACE VIEW customer_360 AS
SELECT
    ca.customer_id,
    ca.age_range,
    ca.gender,
    ca.region,
    ca.customer_category,

    acc.account_id,
    acc.account_type,
    acc.account_open_date,
    t.account_balance,

    t.transaction_id,
    t.transaction_date,
    t.transaction_amount,
    t.transaction_type,
    ca.transaction_frequency,

    ap.product_type,
    ap.product_subscription_date,

    al.loan_amount,
    al.loan_status,

    ac_card.card_type
FROM stg_transactions t
JOIN stg_accounts acc
    ON acc.account_id = t.account_id
JOIN stg_dispositions d
    ON d.account_id = acc.account_id
    AND d.disposition_type = 'OWNER'
JOIN customer_attributes ca
    ON ca.customer_id = d.customer_id
LEFT JOIN agg_loans al
    ON al.account_id = acc.account_id
LEFT JOIN agg_cards ac_card
    ON ac_card.account_id = acc.account_id
LEFT JOIN agg_products ap
    ON ap.account_id = acc.account_id;
