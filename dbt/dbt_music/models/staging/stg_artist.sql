{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_music_staging.stg_artist: plain cast of bv_artist.
select
    cast(artist_id   as integer) as artist_id,
    artist_name,
    cast(label_id    as integer) as label_id
from {{ source('bv_csv_music', 'bv_artist') }}
