{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_analytics.iv_sales: a CONSUMPTION product. It only reads the gold databases of
-- other data products, never a raw layer. A ref() does not cross dbt projects: these
-- inputs are declared as `sources` (see _sources.yml).
-- It inherits the Global Security Policies across databases: the tags stay on the
-- producers' columns, nothing is re-declared here.
select
    il.invoice_id,
    inv.customer_id,
    inv.customer_name,
    cat.track_title,
    cat.label_id,
    cat.label_name,
    cat.unit_price,
    cat.cost_price,
    il.quantity
from {{ source('sales_product', 'iv_invoice_line') }} il
    join {{ source('sales_product', 'iv_invoices') }} inv on il.invoice_id = inv.invoice_id
    join {{ source('music_product', 'iv_catalog') }}  cat on il.track_id   = cat.track_id
