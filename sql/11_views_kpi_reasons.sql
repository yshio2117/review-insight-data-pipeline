-- 1) Enrich reasons with review metadata (date/source). Join on (review_id, run_id) to avoid cross-run mixing.
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_reasons_enriched` AS
SELECT
  r.run_id,
  rv.source_file,
  rv.source,
  rv.posted_at_iso,
  DATE(rv.posted_at_iso) AS posted_date,
  rv.ingested_at,
  rv.review_text,
  r.sentiment_type,
  r.entity,
  r.issue_category,
  r.confidence,
  ARRAY_TO_STRING(r.subject, ',') AS subject, -- REPEATED STRING
  r.predicate,
  r.review_id,
  r.reason_id
FROM `{REVIEW_REASONS_TABLE_ID}` r
JOIN `{REVIEW_VALIDATED_TABLE_ID}_dedup` rv
  ON r.review_id = rv.review_id
 AND r.run_id = rv.run_id
WHERE rv.is_valid = TRUE
;

-- When you want to see only one reason per review id (the one with highest confidence), to avoid double-counting in KPIs
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review` AS
SELECT
  * EXCEPT(rn)
FROM (
  SELECT
    r.run_id,
    rv.source_file,
    rv.source,
    DATE(rv.posted_at_iso) AS posted_date,
    rv.review_text,
    r.sentiment_type,
    r.entity,
    r.issue_category,
    r.confidence,
    r.subject as subject_array, -- keep the original array for later use
    ARRAY_TO_STRING(r.subject, ',') AS subject,
    r.predicate,
    r.review_id,
    r.reason_id,

    ROW_NUMBER() OVER (
      PARTITION BY r.run_id, r.review_id, r.sentiment_type
      ORDER BY r.confidence DESC, r.reason_id ASC
    ) AS rn
  FROM `{REVIEW_REASONS_TABLE_ID}` r
  JOIN `{REVIEW_VALIDATED_TABLE_ID}_dedup` rv
    ON r.review_id = rv.review_id
   AND r.run_id = rv.run_id
  WHERE rv.is_valid = TRUE
)
WHERE rn = 1;

-- 2) Daily KPI: counts by (sentiment, entity, issue_category). This can be used for heatmap
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_reason_categories_daily` AS
SELECT
  run_id,
  source_file,
  source,
  posted_date,
  sentiment_type,
  entity,
  issue_category,
  COUNT(*) AS reason_count,
  COUNT(DISTINCT review_id) AS review_count,
  AVG(confidence) AS avg_confidence
FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`
GROUP BY run_id, source_file, source, posted_date, sentiment_type, entity, issue_category
;

-- entity-level KPI (ignoring issue_category) 
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_entity_counts` AS
SELECT
  run_id,
  source_file,
  source,
  posted_date,
  sentiment_type,
  entity,
  COUNT(*) AS review_count,          -- top1を取っているので、1行=1review扱い
  AVG(confidence) AS avg_confidence
FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`
GROUP BY run_id, source_file, source, posted_date, sentiment_type, entity;


-- issue_category-level KPI (ignoring entity) 
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_issue_category_counts` AS
SELECT
  run_id,
  source_file,
  source,
  posted_date,
  sentiment_type,
  issue_category,
  COUNT(*) AS review_count,
  AVG(confidence) AS avg_confidence
FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`
GROUP BY run_id, source_file, source, posted_date, sentiment_type, issue_category;


-- 3) Top (subject, predicate) pairs
-- subject is REPEATED, so UNNEST it (1 reason row may produce multiple subject tokens)
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_top_subject_predicate` AS
SELECT
  run_id,
  source_file,
  source,
  posted_date,
  sentiment_type,
  s AS subject_token,
  predicate,
  COUNT(*) AS pair_count,
  COUNT(DISTINCT review_id) AS review_count,
  AVG(confidence) AS avg_confidence
FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`,
UNNEST(subject_array) AS s
GROUP BY run_id, source_file, source, posted_date, sentiment_type, subject_token, predicate
;

-- entity/issue_category coverage: how many reasons have these fields filled in
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_entity_issue_coverage` AS
SELECT
  COUNT(*) AS total_records,

  COUNTIF(entity IS NOT NULL) AS entity_filled_count,
  SAFE_DIVIDE(COUNTIF(entity IS NOT NULL), COUNT(*)) AS entity_coverage_rate,

  COUNTIF(issue_category IS NOT NULL) AS issue_category_filled_count,
  SAFE_DIVIDE(COUNTIF(issue_category IS NOT NULL), COUNT(*)) AS issue_category_coverage_rate

FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`;



-- 4) Extraction & entity &issue_category coverage (per run&source file): among valid reviews, how many have the extracted reasons
CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET_ID}.v_kpi_extraction_coverage_by_run` AS
WITH valid_reviews AS (
  SELECT
    run_id,
    source_file,
    COUNT(review_id) AS valid_review_count
  FROM `{REVIEW_VALIDATED_TABLE_ID}_dedup`
  WHERE is_valid = TRUE
  GROUP BY run_id, source_file
),
reviews_with_reasons AS (
  SELECT
    run_id,
    source_file,
    COUNT(DISTINCT review_id) AS reviews_with_any_reason,
    COUNT(DISTINCT IF(sentiment_type = "negative", review_id, NULL)) AS reviews_with_negative_reason,
    COUNTIF(entity IS NOT NULL AND sentiment_type = "negative") AS entity_filled_count,
    COUNTIF(issue_category IS NOT NULL AND sentiment_type = "negative") AS issue_category_filled_count
  FROM `{PROJECT_ID}.{DATASET_ID}.v_reasons_top1_per_review`
  GROUP BY run_id, source_file
)
SELECT
  vr.run_id,
  vr.source_file,
  vr.valid_review_count,
  COALESCE(rr.reviews_with_any_reason, 0) AS reviews_with_any_reason,
  SAFE_DIVIDE(COALESCE(rr.reviews_with_any_reason, 0), vr.valid_review_count) AS extraction_coverage_any,
  COALESCE(rr.reviews_with_negative_reason, 0) AS reviews_with_negative_reason,
  SAFE_DIVIDE(COALESCE(rr.reviews_with_negative_reason, 0), vr.valid_review_count) AS extraction_coverage_negative,
  COALESCE(rr.entity_filled_count, 0) AS entity_filled_count,
  SAFE_DIVIDE(COALESCE(rr.entity_filled_count, 0), vr.valid_review_count) AS entity_coverage_negative,
  COALESCE(rr.issue_category_filled_count, 0) AS issue_category_filled_count,
  SAFE_DIVIDE(COALESCE(rr.issue_category_filled_count, 0), vr.valid_review_count) AS issue_category_coverage_negative
FROM valid_reviews vr
LEFT JOIN reviews_with_reasons rr
  ON vr.run_id = rr.run_id
 AND vr.source_file = rr.source_file
;