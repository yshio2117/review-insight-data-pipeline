from config.settings import SENTIMENT_LABELS


def validate_reason_records(reason_records,lexicons):
    """validate reason records based on the following criteria:

    - if there is a reason_id&review_id&run_id for each reason record
    - if the confidence value is from 0 to 1
    - if there is a subject and predicate for each reason record
    - if there is a sentiment_type and it is in SENTIMENT_LABELS(e.g., "Negative", "Positive")
    - if the entity and issue_category are either None or in the predefined lexicons

    Note: if a record is invalid, currently we raise a ValueError with the reason for invalidation and stop the whole program. 
    """

    for records_per_review in reason_records:
        for record in records_per_review:

            if not 0 <= record["confidence"] <= 1:
                raise ValueError("Invalid confidence")
            if "reason_id" not in record or "review_id" not in record or "run_id" not in record:
                raise ValueError("Missing reason_id, review_id, or run_id")
            if "subject" not in record or "predicate" not in record:
                 raise ValueError("Missing subject or predicate")
            if "sentiment_type" not in record or record["sentiment_type"] not in SENTIMENT_LABELS:
                raise ValueError("Missing or invalid sentiment_type")
            
            if record["entity"] is not None and record["entity"] not in lexicons["entity"]["entity"].values:
                raise ValueError("Invalid entity category")
            if record["issue_category"] is not None and record["issue_category"] not in lexicons["issue"]["issue_category"].values:
                raise ValueError("Invalid issue category")  
    
    print("All reason records are valid.")
    