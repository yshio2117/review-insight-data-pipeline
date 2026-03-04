from datetime import datetime, date, timezone, timedelta




def is_invalid_review_text(review):
    """
    validate review_text and add is_valid and invalid_reason

    Parameters
    ----------
    review : dict
        e.g, {'review_text':'<review_text>', ...}


    Returns
    review : dict
        e.g. {'review_text':<review_text>, 'is_valid':True, 'invalid_reason':[]}  (if valid)
        e.g. {'review_text':<review_text>, 'is_valid':False, 'invalid_reason':['review_text length is too long']} (if invalid)
    -------
    """

    review_text = review.get('review_text')

    if not isinstance(review_text, str):
        review['is_valid'] = False
        review['invalid_reason'].append("review_text is not a string")
        return review

    # if review_text is None or review_text.strip() == "":
    if not review_text.strip():
        review['is_valid'] = False
        review['invalid_reason'].append("review_text is empty")
        return review
        
    # if the length of review_text is too long or too short
    len_text = len(review_text.strip())
    if len_text > 500: #temp
        review['is_valid'] = False
        review['invalid_reason'].append("review_text length is too long")
        return review
    if len_text < 5: #temp
        review['is_valid'] = False
        review['invalid_reason'].append("review_text length is too short")
        return review

    return review



def is_invalid_posted_at(review,posted_at_required=False):
    """
    Validate posted_at using both raw posted_at and normalized posted_at_iso.

    Parameters
    ----------
    review : dict
        e.g. {'posted_at':..., 'posted_at_iso':...,...}
    posted_at_required : bool
        if True, missing/empty posted_at becomes invalid.

    Returns
    -------
    review : dict
         e.g. {'posted_at':..., 'posted_at_iso':..., 'is_valid':False, 'invalid_reason':['posted_at is missing']...}, ...

    Validation rules:
    1. if posted_at(raw) is empty/None → invalid (MISSING) or OK (if not required)
    2. if posted_at(raw) exists but posted_at_iso is None → invalid (PARSE_FAILED)
    3. if posted_at_iso exists but not in UTC nor parseable → invalid (NOT_UTC or PARSE_FAILED)
    """

    reasons = list(review.get("invalid_reason", []))

    raw = review.get("posted_at")
    iso = review.get("posted_at_iso")

    raw_is_missing = (raw is None) or (isinstance(raw, str) and not raw.strip()) or (not isinstance(raw, str))

    # 1) Missing raw posted_at
    if raw_is_missing:
        if posted_at_required:
            reasons.append("posted_at is missing")

    # 2) Raw exists but normalization filed
    raw_has_value = isinstance(raw, str) and bool(raw.strip())
    if raw_has_value and iso is None:
        reasons.append("posted_at parse failed")

    # 3) If iso exists, validate it is parseable and UTC
    if iso is not None:
        try:
            dt = datetime.fromisoformat(iso)

            # Must be timezone-aware and in UTC
            if dt.tzinfo is None:
                reasons.append("posted_at is not UTC")
            else:
                dt_utc = dt.astimezone(timezone.utc)
                if dt_utc.utcoffset() != timezone.utc.utcoffset(dt_utc):
                    reasons.append("posted_at is not UTC")


        except ValueError:
            # iso string itself is invalid
            reasons.append("posted_at parse failed")

    review["invalid_reason"].extend(reasons)
    if len(reasons) > 0:
        review["is_valid"] = False

    return review


def is_invalid_source(review, seen_reviews):
    """
    Validate source, source_id and check duplicates based on them
    
    Parameters
    ----------
    review : dict
        e.g. {'source':..., 'source_id':..., ...}
    seen_reviews : set of tuple
        set of (source, source_id) pairs seen so far for duplicate check(only for reviews with valid source and source_id)
    Returns
    -------
    review : dict
        e.g. {'source':..., 'source_id':..., 'is_valid':False, 'invalid_reason':['Either source_id or source is missing for review_id generation']} (if invalid)

    seen_reviews : set of tuple
        updated set of (source, source_id) pairs with the current review's source and source_id added if valid

    """

    source_id = review.get("source_id")
    source = review.get("source")

    if not source or not source_id:
        review['is_valid'] = False
        review['invalid_reason'].append("Either source_id or source is missing for review_id generation")
    else:
        # check duplicates based on source and source_id
        if (source, source_id) in seen_reviews:
            review['is_valid'] = False
            review['invalid_reason'].append("Duplicate review based on source and source_id")
        else:
            seen_reviews.add((source, source_id))

    return review, seen_reviews


def sort_key(doc): 
    if doc.get("is_valid") is False:
        return (True, datetime.min)
    else:
        return (False, doc.get("posted_at") or datetime.min)


def validate_reviews(reviews):
    """
    Validate review data(source, source_id, review_text, posted_at)

    Parameters
    ----------
    reviews : list of dict
        [{'review_id':'', 'review_text':..., 'posted_at':..., 'is_valid':..., 'invalid_reason':...}, ...]
        
    Returns
    -------
    valid_reviews : list of dict
        e.g. [{'review_id':'', 'review_text':..., 'posted_at':...,'is_valid':True, 'invalid_reason':[]}, ...] (only valid reviews)
    invalid_reviews : list of dict
        e.g. [{'review_id':'', 'review_text':..., 'posted_at':...,'is_valid':False, 'invalid_reason':['reason1','reason2']}, ...] (only invalid reviews)
    """ 

    invalid_reasons = []
    seen_reviews = set() # to track seen (source, source_id) pairs for duplicate check
    
    for review in reviews:

        review['is_valid'] = True # set default value as True, and change to False if any validation fails
        review['invalid_reason'] = [] # set default value as empty list, and append reason if any validation fails

        # validate source_id, source and check duplicated reviews based on them. 
        review,seen = is_invalid_source(review,seen_reviews)        
        # validate review_text
        review = is_invalid_review_text(review)
        # validate posted_at and posted_at_iso. Set posted_at_required as False, if missing posted_at should be treated as valid.
        review = is_invalid_posted_at(review, posted_at_required=True)

        review["invalid_reason"] = sorted(set(review["invalid_reason"]))

    return reviews
