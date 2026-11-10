{{ config(
    folder=var('denodo').folders.integration
) }}
-- chinook_music.iv_catalog: the PUBLISHED data product. This is where the join happens:
-- the gold assembles the staging views and only publishes the columns a consumer needs
-- (no album_id nor artist_id, which are technical keys).
-- label_id stays: it carries the scope_label tag (the criterion of the buyer masking).
select
    t.track_id,
    t.track_title,
    al.album_title,
    ar.artist_name,
    l.label_id,
    l.label_name,
    t.unit_price,
    t.cost_price
from {{ ref('stg_track') }}  t
    join {{ ref('stg_album') }}  al on t.album_id   = al.album_id
    join {{ ref('stg_artist') }} ar on al.artist_id = ar.artist_id
    join {{ ref('stg_label') }}  l  on ar.label_id  = l.label_id
