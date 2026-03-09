### Table: `review_raw` (RAW)
**Purpose:** Raw data layer that loads reviews from CSV without any transformation.

**Grain:** 1 row per ingested record per run

**Keys:**
row_id: UUIDv4 (technical key per ingestion row)
review_id: UUIDv5(source_id, source) (deterministic business key; stable across runs)

### Table: `review_validated` (VAL)
**Purpose:** Add normalization and validation outputs for downstream extraction and BI processes."

**Grain:** 1 row per ingested record per run (1:1 with review_raw via row_id)

**Keys:**
row_id: UUIDv4 (technical key per ingestion row)
review_id: Deterministic UUIDv5 generated from (source_id, source), deterministic business key; stable across runs

**Partitioning:**
- Partition: `posted_at_iso`
- Cluster: `review_id`

### `review_validated_dedup` (VIEW)
**Purpose:** Eliminate duplicates in review_validated (multiple ingestions of the same review_id) and provide a one row per review_id dataset for BI

**Grain:** 1 row per review_id
Dedup rule: select the latest ingested record per review_id


The view selects the most recent record per `review_id`
using the `ingested_at` timestamp:
```sql
SELECT *
FROM (
    SELECT *,
           ROW_NUMBER() OVER (
               PARTITION BY review_id
               ORDER BY ingested_at DESC
           ) AS rn
    FROM review_validated
)
WHERE rn = 1
```

### Table: `review_reasons` (FACT)
**Purpose:** Structure the 'reasons' extracted from review text so they can be aggregated in a dashboard (e.g., by issue/entity and confidence)

**Grain:** 1 row per extracted reason

**Keys:** reason_id (technical key per ingestion row)
FK/Join: review_id → review_validated.review_id