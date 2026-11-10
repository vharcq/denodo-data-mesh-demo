{{ config(
    folder=var('denodo').folders.reporting,
    alias='agg_sales_by_label',
    materialized='table'
) }}
-- Materialized reporting view: materialized='table' => CACHE FULL NOEXPIRE + preload.
-- Reminder: it really reads the sources on every run.
select
    label_name,
    sum(quantity)                             as units_sold,
    sum(quantity * unit_price)                as revenue,
    sum(quantity * (unit_price - cost_price)) as margin
from {{ ref('iv_sales') }}
group by label_name
