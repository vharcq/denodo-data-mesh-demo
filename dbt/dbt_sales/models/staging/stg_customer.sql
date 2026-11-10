{{ config(folder=var('denodo').folders.integration) }}
-- chinook_sales_staging.stg_customer: plain cast of bv_customer.
select
    cast(customer_id   as integer) as customer_id,
    cast(customer_name as varchar) as customer_name,
    cast(email         as varchar) as email
from {{ source('bv_csv_sales', 'bv_customer') }}
