{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_music_staging.stg_album: plain cast of bv_album.
select
    cast(album_id    as integer) as album_id,
    album_title,
    cast(artist_id   as integer) as artist_id
from {{ source('bv_csv_music', 'bv_album') }}
