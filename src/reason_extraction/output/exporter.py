import csv
import os
import copy
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from pathlib import Path
from config.settings import BASE_DIR



def export_reason_records_to_csv(reason_records, filename):

    fieldnames = ['sentiment_type','entity','issue_category','confidence','subject','predicate','review_id','reason_id','run_id']  # order of columns in output CSV
    with open(BASE_DIR / "data/output/{0}.csv".format(filename), "w", encoding="utf_8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reason_records)

    print("Exported reason records to data/output/{0}.csv".format(filename))



def load_reason_records_to_bigquery(reason_records):


    schema = [
        bigquery.SchemaField(
            "sentiment_type",
            "STRING",
            mode="REQUIRED",
            description="Sentiment type (e.g., 'negative','positive')"
        ),
        bigquery.SchemaField(
            "entity",
            "STRING",
            description="Extracted entity category (e.g., 'room','service','location' etc.)"
        ),
        bigquery.SchemaField(
            "issue_category",
            "STRING",
            description="Extracted issue category (e.g., 'cleanliness','staff behavior','amenities' etc.)"
        ),
        bigquery.SchemaField(
            "confidence",
            "FLOAT64",
            mode="REQUIRED",
            description="Extraction Confidence score between 0 and 1"
        ),
        bigquery.SchemaField(
            "subject",
            "STRING",
            mode="REPEATED",
            description="Extracted negative/positive subject (main reason)"
        ),
        bigquery.SchemaField(
            "predicate",
            "STRING",
            description="Extracted negative/positive predicate (main reason)"
        ),

        bigquery.SchemaField(
            "review_id",
            "STRING",
            mode="REQUIRED",
            description="Foreign key to reviews table"
        ),
        bigquery.SchemaField(
            "reason_id",
            "STRING",
            mode="REQUIRED",
            description="Unique ID of the negative/positive reason (generated UUID)"
        ),
        bigquery.SchemaField(
            "run_id",
            "STRING",
            mode="REQUIRED",
            description="Run ID for tracking"
        ),
    ]

    client = bigquery.Client()
    project_id = os.getenv("PROJECT_ID")
    dataset_id = os.getenv("DATASET_ID")
    table_id = "review_reasons"

    reasons_table = f"{project_id}.{dataset_id}.{table_id}"

    # load to reasons table
    load_job = client.load_table_from_json(
        reason_records,
        reasons_table,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            create_disposition="CREATE_IF_NEEDED",
            clustering_fields=["review_id"], # cluster by review_id to optimize query performance when joining with reviews table
        ),
    )

    load_job.result()
    print(f"Loaded reason records to BigQuery: {reasons_table}.")


def export_reasons(reason_records,args):


    # for local CSV, add suffix to the filename (e.g., hotel_reviews_reasons.csv)
    filename = Path(args.input_file).stem + "_reasons"

    # make reason_records flat list
    reason_records = [item for sublist in reason_records for item in sublist]
    # to CSV
    if args.output == "local":
        export_reason_records_to_csv(
                                reason_records,
                                filename=filename
                                )
    else:            
        load_reason_records_to_bigquery(
                                reason_records
                                )


