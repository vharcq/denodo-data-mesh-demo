{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_finance.iv_customer_statement: what each customer was invoiced, line by line,
-- with the contact e-mail and the margin inputs. Nothing here mentions security.
select
    inv.invoice_id,
    inv.customer_id,
    inv.customer_name,
    inv.email,
    cat.label_name,
    cat.track_title,
    il.quantity,
    cat.unit_price,
    cat.cost_price
from {{ source('sales_product', 'iv_invoice_line') }} il
    join {{ source('sales_product', 'iv_invoices') }} inv on il.invoice_id = inv.invoice_id
    join {{ source('music_product', 'iv_catalog') }}  cat on il.track_id   = cat.track_id
