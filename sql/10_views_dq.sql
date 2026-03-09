-- basic metrics by run and source file, including breakdown of invalid reasons
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_dq_metrics_by_run` AS
WITH base AS (
  SELECT
    run_id,
    source_file,
    ingested_at,
    is_valid,
    IFNULL(invalid_reason, []) AS invalid_reason
  FROM `{PROJECT_ID}.{DATASET_ID}.{REVIEW_VALIDATED_TABLE_ID}`
),
reason_flags AS (
  SELECT
    run_id,
    source_file,
    ingested_at,
    is_valid,
    invalid_reason,

    -- check if each specific reason is present in the invalid_reason array
    ('Either source_id or source is missing for review_id generation'
      IN UNNEST(invalid_reason)) AS r_missing_source_or_source_id,

    ('posted_at is missing'
      IN UNNEST(invalid_reason)) AS r_posted_at_missing,

    ('posted_at parse failed'
      IN UNNEST(invalid_reason)) AS r_posted_at_parse_failed,

    ('review_text is empty'
      IN UNNEST(invalid_reason)) AS r_review_text_empty,

    ('review_text length is too short'
      IN UNNEST(invalid_reason)) AS r_review_text_too_short,

    ('review_text length is too long'
      IN UNNEST(invalid_reason)) AS r_review_text_too_long,

    ('Duplicate review based on source and source_id'
      IN UNNEST(invalid_reason)) AS r_duplicate

  FROM base
)

SELECT
  run_id,
  source_file,

  -- min & max ingestion times for the run time
  MIN(ingested_at) AS run_started_at,
  MAX(ingested_at) AS run_last_seen_at,

  COUNT(*) AS total_rows,
  -- unique_reviews = Neither duplicate nor missing source/source_id
  COUNTIF(NOT r_duplicate AND NOT r_missing_source_or_source_id) AS unique_reviews,

  COUNTIF(is_valid IS TRUE) AS rows_valid,
  COUNTIF(is_valid IS FALSE) AS rows_invalid,
  SAFE_DIVIDE(COUNTIF(is_valid IS TRUE), COUNT(*)) AS valid_rate,

  -- Required fields completeness
  COUNTIF(r_missing_source_or_source_id) AS missing_source_or_source_id_rows,
  COUNTIF(r_review_text_empty) AS missing_review_text_rows,
  COUNTIF(r_posted_at_missing) AS missing_posted_at_rows,
  COUNTIF(r_posted_at_parse_failed) AS posted_at_parse_failed_rows,
  SAFE_DIVIDE(COUNTIF(r_posted_at_parse_failed), COUNT(*)) AS posted_at_parse_failed_rate,

  -- Length filter metrics
  COUNTIF(r_review_text_too_short) AS too_short_rows,
  COUNTIF(r_review_text_too_long)  AS too_long_rows,
  SAFE_DIVIDE(
    COUNTIF(r_review_text_too_short) + COUNTIF(r_review_text_too_long),
    COUNT(*)
  ) AS length_out_of_range_rate,

  -- Duplicate metrics
  COUNTIF(r_duplicate) AS duplicate_rows,
  SAFE_DIVIDE(COUNTIF(r_duplicate), COUNT(*)) AS duplicate_rate

FROM reason_flags
GROUP BY run_id, source_file;



-- Breakdown of invalid reasons
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_dq_invalid_reasons_by_run` AS
SELECT
  run_id,
  source_file,
  reason AS invalid_reason,
  COUNT(*) AS rows_count
FROM `{PROJECT_ID}.{DATASET_ID}.{REVIEW_VALIDATED_TABLE_ID}`, -- Use the non-deduped table to get all invalid reasons, including duplicates
UNNEST(invalid_reason) AS reason
GROUP BY run_id, source_file, invalid_reason
ORDER BY run_id, rows_count DESC
;