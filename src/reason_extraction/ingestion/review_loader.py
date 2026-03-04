import csv
import os
import sys
import uuid
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from pathlib import Path
from config.settings import BASE_DIR



def make_run_id(prefix="reviews"):
    """
    Generate a run ID with the format: {prefix}_{timestamp}_{random}, where:
    - prefix: a string prefix for the run ID (default: "reviews")
    - timestamp: current UTC time in the format YYYYMMDDTHHMMSSZ
    - random: a random 8-character hexadecimal string
    """

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rand = uuid.uuid4().hex[:8]
    return f"{prefix}_{ts}_{rand}"


def read_reviews_csv_with_metadata(args):

    """
    Read a CSV and add ingestion metadata columns:
      - source_file: the input file name (as string)
      - row_number:  1-based row number within the CSV (excluding header)
      - ingested_at: UTC timestamp when this function was called (batch timestamp)
      - row_id:      UUID v4 per row (string)

    Returns:
      List of dictionaries (one per row)
    """

    file_path = args.input_file

    with open(BASE_DIR / "{0}".format(file_path), "r", encoding="utf_8", newline="") as f:
        reader = csv.DictReader(f)

        source_file = Path(file_path).name
        ingested_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
        if args.run_id:
            run_id = args.run_id
        else:
            run_id = make_run_id()

        rows = []

        for idx, row in enumerate(reader, start=1):
            new_row = {
                "source_file": source_file,
                "row_number": idx,
                "ingested_at": ingested_at,
                "row_id": str(uuid.uuid4()),
                "run_id": run_id,
            }

            # add the original row data to the new row
            new_row.update(row)

            rows.append(new_row)

    return rows


def raw_reviews_to_csv(reviews, filename):
    """
    Output raw reviews data to CSV
    Parameter
    ----------
    reviews : list of dict
          [{'source','source_id','review_text', 'posted_at', 'user_name', 'source_file','row_number','row_id','ingested_at','run_id'}, ...]       
    filename : str
        output filename（e.g.: "hotel_reviews_validated"）
    Returns
    -------
    None

    """ 


    fieldnames = ['source','source_id','review_text', 'posted_at', 'user_name', 'source_file','row_number','row_id','ingested_at','run_id']
    with open(BASE_DIR / "data/output/{0}.csv".format(filename), "w", encoding="utf_8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)

    print("Exported raw reviews file to data/output/{0}.csv".format(filename))
    
   
def raw_reviews_to_bq(reviews):
    """
    Load raw reviews data to BigQuery 

    Note: run_id + source_row_number is used to identify each review in the raw table
    ----------
    reviews : list of dict
          [{'source','source_id','review_text', 'posted_at', 'user_name', 'source_file','row_number','row_id','ingested_at','run_id'}, ...]       

    Returns
    -------
    None

    """ 


    schema = [
        bigquery.SchemaField(
            "source",
            "STRING",
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
            "ingested_at", 
            "TIMESTAMP",
            mode="REQUIRED",
            description="Ingested date and time of the review"
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
    table_id = "review_raw"

    # check if dataset exists, if not create it
    dataset_ref = f"{project_id}.{dataset_id}"
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset exists: {dataset_ref}")
    except NotFound:
        print(f"Dataset {dataset_ref} not found. Creating...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"Dataset {dataset_ref} created.")


    raw_reviews_table = f"{project_id}.{dataset_id}.{table_id}"

    try: 
        raw_reviews_table = client.get_table(raw_reviews_table) # check if raw_reviews_table exists
    except NotFound: 
        # create raw_reviews_table if not exists
        raw_reviews_table = bigquery.Table(raw_reviews_table, schema=schema)
        client.create_table(raw_reviews_table)
        print("Created review_raw table.")


    # load raw_reviews to BigQuery
    load_job = client.load_table_from_json(
        reviews,
        raw_reviews_table,
        job_config=bigquery.LoadJobConfig(
            schema=schema,
            write_disposition="WRITE_APPEND",
        ),
    )

    load_job.result()
    print(f"Loaded raw reviews to BigQuery: {raw_reviews_table}.")


def load_raw_reviews(reviews, args, suffix):

    # for local CSV, add suffix to the filename (e.g., hotel_reviews_raw.csv)
    filename = Path(args.input_file).stem + f"{suffix}"
    if args.output == "local":
        # export to local
        raw_reviews_to_csv(reviews, filename)
    else:
        # export to BigQuery
        raw_reviews_to_bq(reviews)