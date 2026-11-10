{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_music_staging.stg_label: plain cast of bv_label. One stg_ per bv_, no join:
-- staging publishes its entities, the gold assembles them.
select
    cast(label_id   as integer) as label_id,
    label_name
from {{ source('bv_csv_music', 'bv_label') }}
