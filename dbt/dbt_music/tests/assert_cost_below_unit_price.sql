-- Business rule, tested on every build: a track is never bought more expensive than it
-- is sold. A singular dbt test returns the rows that break the rule; zero rows = pass.
select track_id, track_title, unit_price, cost_price
from {{ ref('iv_catalog') }}
where cost_price > unit_price
