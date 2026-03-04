import os
from pathlib import Path
from google.cloud import bigquery
from dotenv import load_dotenv
load_dotenv()

def render_sql(template):
    project_id = os.environ["PROJECT_ID"]
    dataset_id = os.environ["DATASET_ID"]
    return template.format(PROJECT_ID=project_id, DATASET_ID=dataset_id)

def run_sql_file(client, path):
    template = path.read_text(encoding="utf-8")
    sql = render_sql(template)
    job = client.query(sql)
    job.result()

def main():
    client = bigquery.Client()
    for p in sorted(Path("sql").glob("*.sql")):
        print(f"Running: {p}")
        run_sql_file(client, p)

if __name__ == "__main__":
    main()