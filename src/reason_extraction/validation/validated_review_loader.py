import csv
import os
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from pathlib import Path
from config.settings import BASE_DIR

def export_validated_reviews_to_csv(reviews, filename):
    """
    Output validated reviews data to CSV
    Parameter
    ----------
    reviews : list of dict
          [{'review_text':..., 'posted_at':..., 'user_name':..., 'source':..., 'ingested_at':..., 'language':..., 'is_valid':..., 'invalid_reason':..., 'run_id':...}, ...]       
    filename : str
        output filename（e.g.: "hotel_reviews_validated"）
    Returns
    -------
    None

    """ 


    # review_id, posted_at_iso, is_valid, invalid_reason, tokens are added in validated_reviews
    fieldnames = ['source','source_id','review_text', 'posted_at', 'posted_at_iso', 'user_name', 'source_file','row_number','row_id', 'review_id', 'ingested_at', 'is_valid', 'invalid_reason','run_id', 'tokens']
    with open(BASE_DIR / "data/output/{0}.csv".format(filename), "w", encoding="utf_8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)

    print("Exported validated reviews file to data/output/{0}.csv".format(filename))



def load_validated_reviews_to_bq(reviews):
    """
    Load validated reviews data to BigQuery 
    Parameters
    ----------
    reviews : list of dict
          [{'source','source_id','review_text', 'posted_at', 'user_name', 'source_file','row_number','row_id','ingested_at','review_id','posted_at_iso','is_valid','invalid_reason','run_id','tokens'}, ...]       

    Returns
    -------
    None

    """ 


    schema = [
        bigquery.SchemaField(
            "source",
            "STRING",
            mode="REQUIRED",
            description="Source of the review (e.g., tripadvisor,booking.com etc.)"
            ),
        bigquery.SchemaField(
            "source_id",
            "STRING",
            description="Source ID (e.g., review ID from the original source)"
            ),
        bigquery.SchemaField(
            "review_text", 
            "STRING",
            description="review text"
            ),
        bigquery.SchemaField(
            "posted_at", "STRING",
            description="Posted date and time of the review"
            ),
        bigquery.SchemaField(
            "posted_at_iso", "TIMESTAMP", # new field for validated_reviews
            description="Posted date and time of the review in ISO format in UTC timezone"
            ),    
        bigquery.SchemaField(
            "user_name", "STRING",
            description="Name of the user who posted the review"
            ),
        bigquery.SchemaField(
            "source_file",
            "STRING",
            mode="REQUIRED",
            description="Source file name of the review (e.g., hotel_reviews.csv)"
            ),
        bigquery.SchemaField(
            "row_number", "INT64",
            mode="REQUIRED",
            description="Row number of the review in the source file (excluding header)"
            ),
        bigquery.SchemaField(
            "row_id", "STRING",
            mode="REQUIRED",
            description="Unique ID of the review row (generated UUID v4)"
            ),
        bigquery.SchemaField(
            "review_id",
            "STRING",
            description="Unique ID of the review (generated UUID v5 based on source and source_id. If either source or source_id is missing, set review_id to None)"
        ),
        bigquery.SchemaField(
            "ingested_at", 
            "TIMESTAMP",
            mode="REQUIRED",
            description="Ingested date and time of the review"
            ),
        bigquery.SchemaField(
            "is_valid", 
            "BOOL",
            mode="REQUIRED",
            description="Whether the review is valid or not"
            ),
        bigquery.SchemaField(
            "invalid_reason", 
            "STRING",
            mode="REPEATED",  # list
            description="Reason why the review is invalid"
            ),
        bigquery.SchemaField(
            "run_id", 
            "STRING",
            mode="REQUIRED",
            description="Run ID of the review ingestion process"
            ),
    ]

    client = bigquery.Client()
    project_id = os.getenv("PROJECT_ID")
    dataset_id = os.getenv("DATASET_ID")
    table_id = "review_validated"

    # main table
    reviews_table = f"{project_id}.{dataset_id}.{table_id}"
    # dedup view to get the latest ingested review for each review_id, and all invalid reviews with null review_id
    reviews_table_dedup = f"{project_id}.{dataset_id}.{table_id}_dedup"

    try: 
        reviews_table = client.get_table(reviews_table) # check if reviews_table exists
    except NotFound: 
        # create reviews_table if not exists
        reviews_table = bigquery.Table(reviews_table, schema=schema)
        # Set Partition by posted_at_iso
        reviews_table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="posted_at_iso",  
        )
        # set clustering by review_id to optimize query performance when joining with reasons table
        reviews_table.clustering_fields = ["review_id"]
        client.create_table(reviews_table)
        print("Created validated reviews table.")


    # remove reviews['tokens'] before loading to BigQuery, since it's too long data to load.
    reviews = [{k: v for k, v in review.items() if k != "tokens"} for review in reviews]


    # load to reviews_table
    load_job = client.load_table_from_json(
        reviews,
        reviews_table,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            write_disposition="WRITE_APPEND",
        ),
    )

    load_job.result()
    print(f"Loaded validated reviews to BigQuery: {reviews_table}.")


    # 2) dedup view（to get the latest ingested review for each review_id, and all invalid reviews with null review_id）
    dedup_sql = f"""
    CREATE OR REPLACE VIEW `{reviews_table_dedup}` AS
    WITH valid_dedup AS (
      SELECT * EXCEPT(rn)
      FROM (
        SELECT
          r.*,
          ROW_NUMBER() OVER(
            PARTITION BY review_id
            ORDER BY ingested_at DESC, row_id DESC
          ) AS rn
        FROM `{reviews_table}` r
        WHERE review_id IS NOT NULL
      )
      WHERE rn = 1
    ),
    invalid_all AS (
      SELECT * FROM `{reviews_table}`
      WHERE review_id IS NULL
    )
    SELECT * FROM valid_dedup
    UNION ALL
    SELECT * FROM invalid_all
    """
    q = client.query(dedup_sql)
    q.result()
    print(f"Created/Updated dedup view: {reviews_table_dedup}.")



def load_validated_reviews(validated_reviews, args, suffix="_validated"):
    """ Load validated reviews to BigQuery or local CSV based on args.output."""

    # for local CSV, add suffix to the filename (e.g., hotel_reviews_validated.csv)
    filename = Path(args.input_file).stem + f"{suffix}"

    if args.output == "bigquery":
        load_validated_reviews_to_bq(validated_reviews)
    elif args.output == "local":
        export_validated_reviews_to_csv(validated_reviews, filename)
    else:
        raise ValueError(f"Invalid output: {args.output}. Supported outputs are 'bigquery' and 'local'.")

