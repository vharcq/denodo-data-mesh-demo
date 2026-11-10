{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_sales.iv_invoices: the PUBLISHED data product. Invoice x customer join, done in
-- the gold from the two staging views. email = personal data (tag class_pii).
select
    i.invoice_id,
    i.customer_id,
    c.customer_name,
    c.email
from {{ ref('stg_invoice') }} i
    join {{ ref('stg_customer') }} c on i.customer_id = c.customer_id
