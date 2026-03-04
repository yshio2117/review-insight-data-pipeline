from src.reason_extraction.ingestion.review_loader import read_reviews_csv_with_metadata, load_raw_reviews
from src.reason_extraction.ingestion.lexicon_loader import read_lexicons
from src.reason_extraction.validation.review_validater import validate_reviews
from src.reason_extraction.validation.validated_review_loader import load_validated_reviews
from src.reason_extraction.transformation.review_transformer import add_review_id, to_iso_utc, split_reviews_by_validity
from src.reason_extraction.preprocessing.review_preprocessor import preprocess_reviews
from src.reason_extraction.extraction.reason_extractor import extract_reason_records
from src.reason_extraction.transformation.reason_transformer import transform_reason_records
from src.reason_extraction.validation.reason_validater import validate_reason_records
from src.reason_extraction.output.exporter import export_reasons



def run_pipeline(args):
    # 1. ingestion (read CSV file, lexicons and load to BigQuery or local CSV)
    reviews = read_reviews_csv_with_metadata(args)
    lexicons = read_lexicons()
    # load raw reviews to BigQuery or local CSV
    load_raw_reviews(reviews, args, suffix="_raw")

    # 2. transformation s
    # adding review_id by uuid v5 if source_id and source exist
    reviews = add_review_id(reviews)
    # convert posted_at to ISO format in UTC timezone
    reviews = to_iso_utc(reviews)

    # 3. validation (source, source_id, review_text, posted_at, posted_at_iso)
    validated_reviews = validate_reviews(reviews)
    # load validated_reviews to BigQuery or local CSV
    load_validated_reviews(validated_reviews, args, suffix="_validated") 
    # only valid_reviews for next steps
    valid_reviews, invalid_reviews = split_reviews_by_validity(validated_reviews)

    # 4. preprocessing (text normalization, tokenization, and search tokens with sentiment)
    processed_reviews = preprocess_reviews(valid_reviews, lexicons,args)

    # 5. extraction (extracting reason pairs)
    reason_records = extract_reason_records(processed_reviews)

    # 6. transformation of reason records
    reason_records = transform_reason_records(reason_records, processed_reviews, lexicons, args)

    # 7. validation of reason records 
    validate_reason_records(reason_records, lexicons)

    # 8. output reasons to bigquery or csv
    export_reasons(reason_records, args)


