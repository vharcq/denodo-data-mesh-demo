{{ config(folder=var('denodo').folders.integration) }}
-- chinook_sales_staging.stg_invoice_line: invoice lines, cast.
select
    cast(line_id    as integer) as line_id,
    cast(invoice_id as integer) as invoice_id,
    cast(track_id   as integer) as track_id,
    cast(quantity   as integer) as quantity
from {{ source('bv_csv_sales', 'bv_invoice_line') }}
