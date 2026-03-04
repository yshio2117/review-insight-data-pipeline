CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_dq_metrics_by_run` AS
WITH base AS (
  SELECT
    run_id,
    source_file,
    ingested_at,
    source,
    source_id,
    review_id,
    review_text,
    posted_at,
    posted_at_iso,
    is_valid,
    invalid_reason
  FROM `{PROJECT_ID}.{DATASET_ID}.review_validated_dedup`
),
dup_calc AS (
  -- Duplicate definition: same (source, source_id) within the same run_id (only when both are present)
  SELECT
    b.*,
    CASE
      WHEN source IS NOT NULL AND source_id IS NOT NULL
      THEN COUNT(*) OVER (PARTITION BY run_id, source, source_id)
      ELSE 0
    END AS dup_cnt
  FROM base b
)
SELECT
  run_id,
  source_file,

  -- Use ingestion time as the run time anchor for dashboards
  MIN(ingested_at) AS run_started_at,
  MAX(ingested_at) AS run_last_seen_at,

  COUNT(*) AS unique_reviews,
  COUNTIF(is_valid IS TRUE) AS rows_valid,
  COUNTIF(is_valid IS FALSE) AS rows_invalid,  -- Note: Should not write as COUNTIF(is_valid) nor COUNTIF(NOT is_valid) in BigQuery. It's not equal with COUNTIF(is_valid IS FALSE/TRUE) and may pick up unexpected evaluation results..
  SAFE_DIVIDE(COUNTIF(is_valid IS TRUE), COUNT(*)) AS valid_rate,

  -- "Required fields" completeness (value-level checks)
  COUNTIF(source IS NULL OR source = "") AS missing_source_rows,
  COUNTIF(source_id IS NULL OR source_id = "") AS missing_source_id_rows,
  COUNTIF(review_text IS NULL OR review_text = "") AS missing_review_text_rows,

  -- posted_at is optional, but track nulls/parse failures
  COUNTIF(posted_at IS NULL OR posted_at = "") AS missing_posted_at_rows,
  COUNTIF(
    (posted_at IS NOT NULL AND posted_at != "")
    AND posted_at_iso IS NULL
  ) AS posted_at_parse_failed_rows,
  SAFE_DIVIDE(
    COUNTIF((posted_at IS NOT NULL AND posted_at != "") AND posted_at_iso IS NULL),
    COUNT(*)
  ) AS posted_at_parse_failed_rate,

  -- Length filter metrics (based on actual text length)
  COUNTIF(CHAR_LENGTH(COALESCE(review_text, "")) < 5) AS too_short_rows,
  COUNTIF(CHAR_LENGTH(COALESCE(review_text, "")) > 500) AS too_long_rows,
  SAFE_DIVIDE(
    COUNTIF(CHAR_LENGTH(COALESCE(review_text, "")) < 5)
    + COUNTIF(CHAR_LENGTH(COALESCE(review_text, "")) > 500),
    COUNT(*)
  ) AS length_out_of_range_rate,

  -- Duplicate metrics (computed)
  COUNTIF(dup_cnt > 1) AS duplicate_rows,
  SAFE_DIVIDE(COUNTIF(dup_cnt > 1), COUNT(*)) AS duplicate_rate,
  COUNT(*) + COUNTIF(dup_cnt > 1) AS total_rows
FROM dup_calc
GROUP BY run_id, source_file


-- Breakdown of invalid reasons (good for a bar chart in Looker Studio)
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_dq_invalid_reasons_by_run` AS
SELECT
  run_id,
  source_file,
  reason AS invalid_reason,
  COUNT(*) AS rows_count
FROM `{PROJECT_ID}.{DATASET_ID}.review_validated`, -- Use the non-deduped table to get all invalid reasons, including duplicates
UNNEST(invalid_reason) AS reason
GROUP BY run_id, source_file, invalid_reason
ORDER BY run_id, rows_count DESC
;


-- Optional: DQ metrics by run_id + source (helps spot source-specific issues)
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_dq_metrics_by_run_source` AS
WITH base AS (
  SELECT
    run_id, source_file, source, source_id, review_text, posted_at, posted_at_iso, is_valid
  FROM `{PROJECT_ID}.{DATASET_ID}.review_validated_dedup`
)
SELECT
  run_id,
  source_file,
  source,
  COUNT(*) AS rows_total,
  COUNTIF(is_valid IS TRUE) AS rows_valid,
  SAFE_DIVIDE(COUNTIF(is_valid IS TRUE), COUNT(*)) AS valid_rate,
  COUNTIF((posted_at IS NOT NULL AND posted_at != "") AND posted_at_iso IS NULL) AS posted_at_parse_failed_rows
FROM base
GROUP BY run_id, source_file, source
;