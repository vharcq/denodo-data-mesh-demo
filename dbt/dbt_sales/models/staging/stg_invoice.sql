{{ config(folder=var('denodo').folders.integration) }}
-- chinook_sales_staging.stg_invoice: plain cast of bv_invoice (no customer join here).
select
    cast(invoice_id  as integer) as invoice_id,
    cast(customer_id as integer) as customer_id
from {{ source('bv_csv_sales', 'bv_invoice') }}
