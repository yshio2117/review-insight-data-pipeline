import csv
from pathlib import Path
import argparse
from dotenv import load_dotenv
load_dotenv()
from src.reason_extraction.pipeline.review_pipeline import run_pipeline
from config.settings import SENTIMENT_LABELS


def validate_input_file(path_str):

    path = Path(path_str)

    # check file extension
    if path.suffix.lower() != ".csv":
        raise argparse.ArgumentTypeError(
            "Input file must be a .csv file."
        )

    # check if file exists
    if not path.exists():
        raise argparse.ArgumentTypeError(
            "Input file does not exist."
        )

    # check if it's a file
    if not path.is_file():
        raise argparse.ArgumentTypeError(
            "Input path is not a file."
        )

    return path 


def validate_sentiment(sentiment):

    # check if the sentiment label is valid
    if sentiment not in SENTIMENT_LABELS:
        raise argparse.ArgumentTypeError(
            f"Invalid sentiment. Choose from {SENTIMENT_LABELS}."
        )
    return sentiment

    
def parse_args():

    parser = argparse.ArgumentParser()
    # review file name
    parser.add_argument(
        "--input-file", 
        required=True,
        type=validate_input_file,
        help="Input CSV file (required)"
    )
    # which sentiment to extract reasons for
    parser.add_argument(
        "--sentiment", 
        choices=SENTIMENT_LABELS,
        default=SENTIMENT_LABELS[0],
        type=validate_sentiment,
        help=f"Sentiment label for extracting reasons (default: {SENTIMENT_LABELS[0]})"
    )
    # where to output (validated reviews & negative reasons)
    parser.add_argument(
        "--output",
        choices=["bigquery", "local"],
        default="bigquery",
        help="Output destination (default: bigquery)"
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run ID for tracking (default: auto-generated)"
    )

    return parser.parse_args()


def main():
    args = parse_args()
    run_pipeline(args)


if __name__=='__main__':
    
    main()