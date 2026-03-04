# Review Insight Data Pipeline

A lightweight DataOps-style pipeline for extracting negative review reasons using rule-based NLP, storing results in BigQuery, and visualizing KPIs in Looker Studio.

## Overview
This project:

1. Loads negative reviews (e.g., hotel reviews) from CSV  
2. Extracts negative reasons (subject–predicate pairs) using rule-based NLP in Python  
3. Stores the processed results in BigQuery  
4. Visualizes KPIs and negative reasons in Looker Studio  

**Note:** Reviews are currently in Japanese; however, the pipeline is language-independent and can be applied to English or German datasets.

## Demo / Output

- [Output PDF](docs/Report_on_Negative_Review_Reasons.pdf)
- [Looker Studio dashboard](https://lookerstudio.google.com/reporting/a6186eaf-dfec-409e-91ba-79826297d478)



## Architecture
CSV → Python (cleaning + rule-based extraction + validation) → BigQuery → Looker Studio

- Ingestion inputs: a local CSV file and lexicons used to detect negative terms and categorize extracted reasons.
- Processing: Python scripts
- Storage: 3 tables + 1 view (details → [BigQuery Schema](#bigquery-schema))
- BI: Looker Studio (top reasons, trends, data quality metrics)

```mermaid
flowchart LR
  subgraph Local["Local (Python)"]
    CSV["Input CSV (reviews.csv)"]
    LEX["Lexicons (negative + entity + issue)"]
    PIPE["Pipeline (ingest → validate → extract)"]
  end

  subgraph BQ["BigQuery"]
    RAW["review_raw (RAW)"]
    VAL["review_validated (+ dedup view) (VAL)"]
    FACT["reason (FACT)"]
  end

  DASH["Looker Studio Dashboard"]

  CSV --> PIPE
  LEX --> PIPE

  PIPE --> RAW
  PIPE --> VAL
  PIPE --> FACT

  VAL --> DASH
  FACT --> DASH
```

Note: Negative lexicon credit: Japanese Sentiment Dictionary (Volume of Nouns) ver. 1.0, developed by the Inui–Okazaki Laboratory, Tohoku University.
## Dataset
- Default source in this repo: Synthetic (dummy) reviews for a hotel (data/input/sample_thotel_reviews.csv)
  - The pipeline works with real-world reviews as well, as long as they follow the same CSV schema.

- Language: Japanese (current rules are optimized for Japanese text)
### Expected CSV schema
Columns expected in the input CSV:

- source_id (Review ID in the original source. Type: STRING or INT64)
- source (Review source name. Type: STRING; e.g., booking.com, tripadvisor)
- review_text (Review text to analyze. Type: STRING)
- posted_at (When the review was posted. Type: DATE or TIMESTAMP) (optional)
- user_name (Reviewer name. Type: STRING) (optional)


## Extraction Logic (Rule-based)
Goal: extract word-pairs like **(subject, predicate)** from a negative review.

Current rule examples: First, we detect negative terms in each review using the negative lexicon, then extract the paired subject and/or predicate from the same sentence using the rules below:
- When the negative term is a noun: Extract the verb, adjective, or adjectival noun immediately following it within the same sentence as the predicate.
- When the negative term is a verb/adjective/adjectival noun: Extract the noun closest to the negative word appearing earlier in the same sentence as the subject.

[Other rules are here](docs/extraction_rules.md)

<br/>

Output fields:
- `reason_subject` (e.g., “ベッド(Bed)”, “スタッフ(Staff)”, “風呂(Bathroom)”. The subject can be multiple terms)
- `reason_predicate` (e.g., “汚い(dirty)”, “うるさい(noisy)”, “不愛想(unfriendly)”)


Limitations:
- Cannot extract(detect) reasons from 'contextually negative texts' that don’t contain any negative words. (e.g., "隣の部屋から音が聞こえました"("I heard people talking in the next room."))
- Multiple reason pairs can be extracted from one review, but they may not represent different problems: they might describe the same issue using different wording (e.g., S1: Linen / P1: Dirty , S2: Towel / P2: Unpleasant).
- The extracted subject may include multiple tokens and some unnecessary words, since it is difficult to isolate a single subject with the current word-level logic. (e.g., S:['東京'(Tokyo),'ホテル'(hotel),'リネン'(linen)], P:'汚い(dirty)'). To imporove this, we may need deeper analysis as semantic parsing.


## Categorizing logic
Goal: categorize the extracted reasons into **Entity** and **Issue** using the customizable lexicons. 

**Entity:** subject(s) are expected to be matched to one entity which defined in entity_lexicon.csv
e.g., 'リネン'(linen) → Bedding. '自販機'(vending machine) → Facilities

| term   | language | entity     | version |
|--------|----------|------------|---------|
| リネン | ja       | Bedding    | 1       |
| 自販機 | ja       | Facilities | 1       |
| ・・・ | 
Excerpt: entity_lexicon.csv


**Issue:** predicate is expected to be matched to one issue-category which defined in issue_lexicon.csv
e.g., '聞こえる(hear)'→'Noise', '不安(worried)'→'Safety'
| term   | language | issue_category | sentiment | version |
|--------|----------|------------|-----|---------|
| 聞こえる | ja       | Noise    | negative | 1       |
| 不安 | ja       | Safety | negative | 1       |
| ・・・ | 
Excerpt: issue_lexicon.csv

Note: The 'sentiment' column could be set to 'positive' when extracting positive reasons instead of negative ones (currently not implemented).


## Data Quality Checks
Implemented minimal checks for raw reveiws before loading to BigQuery:
- required column presence(`source_id`, `source`, `review_text`, and `posted_at`). `posted_at` can be checked as optional.
- duplicate `reviews` detection: check whether `source_id` and `source` are the same. if so, we consider them to be the duplicated reviews.
- invalid timestamp format handling(`posted_at` and `posted_at_iso`. (`posted_at_iso` will be added as metadata for loading into BigQuery after ingestion.))
- basic length filter to `review_text` (between 5 and 500 characters).

<br/>

Note: Records that do not pass the quality check are flagged as `is_valid = False` and excluded from downstream processing. They can be monitored in the review_validated table.
<br/>


## BigQuery Schema
**review_raw:** raw ingest

**review_validated:** validated reviews + metadata (append-only)

**review_validated_dedup (VIEW):** latest/representative row per review_id

**review_reasons:** extracted reasons

[Tables Detail](docs/data_dictionary.md)

[ER Diagram](docs/er_diagram.md)


## Dashboard (Looker Studio)
- Sample pdf Report (dummy reviews for a hotel) is available here: `docs/Report_on_Negative_Review_Reasons.pdf`.
- [Dashboard link](https://lookerstudio.google.com/reporting/a6186eaf-dfec-409e-91ba-79826297d478)


### Page 1: Data Quality / Pipeline Health
Shows ingestion volume, deduplication impact (total vs unique), valid/invalid rates, and breakdowns for duplicate groups and invalid reasons.


### Page 2: Extracted Reasons Insights
Shows top entities & issue categories, and the entity × issue_category heatmap based on the canonical (top-confidence) reason per review.

### Page 3: Drilldown / Record Explorer
Allows filtering by run and drilling down to validated records and extracted reasons for auditing/debugging.


## Repo Structure
```text
.
├── README.md
├── config
│   ├── __init__.py
│   └── settings.py    # Non-sensitive application settings and constants
├── credentials
├── data
│   ├── input          # place the file here you'd like to analyze
│   │   └── sample_hotel_reviews.csv
│   └── output         # Used for debugging and local development.  
|                      # Outputs a CSV file when the run parameter is set to "--output local".
├── dics
│   ├── entity_lexicon.csv    # for categorizing entity
│   ├── issue_lexicon.csv     # for categorizing issue
│   └── sentiment_lexicon.csv # for detecting a polarity term
├── docs
│   ├── data_dictionary.md
│   ├── er_diagram.md
│   ├── extraction_rules.md
|   └── Report_on_Negative_Review_Reasons.pdf # sample report for hotel reviews (used only dummy data)
├── requirements.txt
├── sql
│   ├── 10_views_dq.sql      # sql for creating DQ views
│   └── 11_views_kpi_reasons.sql  # sql for creating KPI Reason views
├── src
│   ├── __init__.py
│   └── reason_extraction
│       ├── __init__.py
│       ├── main.py          # Entry point for the extraction pipeline
│       ├── apply_sql.py     # Creates BigQuery views for Looker Studio
│       ├── extraction       # Review reason extraction logic
│       ├── ingestion        # Data ingestion module
│       ├── output           # BigQuery loading module
│       ├── pipeline         # Pipeline orchestration
│       ├── preprocessing    # Data preprocessing
│       ├── transformation   # Data transformation
│       └── validation       # Data quality validation
├── tests
```


## Setup

### Requirements

- Python 3.12+
- A Google Cloud project with a BigQuery dataset

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
### Environment Variables
Copy .env.example to .env, then configure the following variables:

`UUID_STRING` – Used to generate a consistent reason_id for identical review texts across different pipeline runs.
Generate one by running:

bash
```
uuidgen
```

`PROJECT_ID` – Your BigQuery project ID.

`DATASET_ID` – Your BigQuery dataset ID.

`GOOGLE_APPLICATION_CREDENTIALS` – Path to your Google Cloud service account key JSON file (set either in your system environment or in .env).


⚠️ Do not commit your service account key file to the repository.

### Run

Place the file you want to analyze in `data/input/`, then run the command below.

(For the required file schema, see [here](#expected-csv-schema)).
```
python -m src.reason_extraction.main \
  --input-file data/input/(your filename).csv  \
  --output bigquery
```

To output the analysis results to `data/output/` instead of BigQuery, run:
```
python -m src.reason_extraction.main \
  --input-file data/input/(your filename).csv  \
  --output local
```

### How to create BigQuery Views
After running main.py, run the command below:
```
python -m src.reason_extraction.apply_sql
```
