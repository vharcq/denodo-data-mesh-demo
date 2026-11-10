{{ config(folder=var('denodo').folders.integration) }}
-- chinook_sales.iv_invoice_line: published invoice lines, read by the analytics product.
select
    line_id,
    invoice_id,
    track_id,
    quantity
from {{ ref('stg_invoice_line') }}
