{{ config(
    folder=var('denodo').folders.business_entities
) }}
-- chinook_sales.be_customer: BUSINESS ENTITY, the customer as a complete object
-- (identity + activity), assembled from the published views of THIS product.
-- Deliberately WITHOUT revenue: the price comes from the Music data product.
-- A metric that needs two domains belongs to the consumption product
-- (chinook_analytics), not to one of the two producers: otherwise Sales depends on
-- Music and the two are no longer independent.
-- email comes from iv_invoices: the class_pii tag set there applies down the query tree.
select
    inv.customer_id,
    inv.customer_name,
    inv.email,
    count(distinct inv.invoice_id) as invoice_count,
    sum(il.quantity)               as units_bought
from {{ ref('iv_invoices') }} inv
    join {{ ref('iv_invoice_line') }} il on il.invoice_id = inv.invoice_id
group by inv.customer_id, inv.customer_name, inv.email
