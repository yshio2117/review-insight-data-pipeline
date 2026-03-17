{{ config(materialized='view') }}

WITH source_data AS (
    SELECT *
    FROM {{ source('pipeline', 'validated') }}
),
valid_dedup AS (
    SELECT *
    FROM source_data
    WHERE review_id IS NOT NULL
    QUALIFY ROW_NUMBER() OVER(
        PARTITION BY review_id
        ORDER BY ingested_at DESC, row_id DESC
    ) = 1
),

invalid_all AS (
    SELECT *
    FROM source_data
    WHERE review_id IS NULL
)

SELECT * FROM valid_dedup
UNION ALL
SELECT * FROM invalid_all