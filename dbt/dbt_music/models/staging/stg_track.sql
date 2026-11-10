{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_music_staging.stg_track: plain cast of bv_track.
-- NB: in VQL, CAST takes SQL type names (integer, decimal(p,s), varchar),
--     not VQL type names (int, text) -> "Exception parsing query near 'int'".
select
    cast(track_id    as integer)       as track_id,
    track_title,
    cast(album_id    as integer)       as album_id,
    cast(unit_price  as decimal(10,2)) as unit_price,
    cast(cost_price  as decimal(10,2)) as cost_price
from {{ source('bv_csv_music', 'bv_track') }}
