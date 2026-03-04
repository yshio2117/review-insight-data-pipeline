import csv
import uuid
from config.settings import BASE_DIR


def remove_duplicate_reasons(sentiment_reasons):
    """
    Remove duplicate reasons (if there are multiple identical subject-predicate pairs)

    Parameters
    ----------
    sentiment_reasons : list of dict
                e.g. [{'subject':[0],'predicate':[3],'sentiment_type':'negative'},{'subject':[0],'predicate':[3],'sentiment_type':'negative'},...]   

    Returns
    -------
    result : list of dict
                e.g. [{'subject':[0],'predicate':[3],'sentiment_type':'negative'}] 
    """ 

    unique = list({
        (tuple(d['subject']), tuple(d['predicate']), d.get('sentiment_type'))
        for d in sentiment_reasons
    })

    removed_duplicates = [
        {'subject': list(s), 'predicate': list(p), 'sentiment_type': st}
        for s, p, st in unique
    ]

    return removed_duplicates


def attach_reason_ids(sentiment_reasons, review):

    for sentiment_reason in sentiment_reasons:
        sentiment_reason['review_id'] = review.get('review_id')
        sentiment_reason["reason_id"] = str(uuid.uuid4())
        sentiment_reason["run_id"] = review.get("run_id")


def split_reason_predicates(sentiment_reasons):
    """
    Split reason predicates when there are multiple predicates

    Parameters
    ----------
    sentiment_reasons : list of dict. Each dict contains lists of subject and predicate indices.
            e.g. [{'predicates':[0,2],'subject':[1],'sentiment_type':'negative'},..]
    Returns
    -------
            e.g. [{'predicate':[0],'subject':[1],'sentiment_type':'negative'},
                  {'predicate':[2],'subject':[1],'sentiment_type':'negative'}..]
    """

    result = []

    for item in sentiment_reasons:
        original_predicates = item.get('predicates', [])
        subject = item.get('subject', [])
        sentiment_type = item.get('sentiment_type', None)
        # Split if there are 2 or more predicates, otherwise keep as is
        if len(original_predicates) >= 2:
            for predicate in original_predicates:
                result.append({
                    'predicate': [predicate],
                    'subject': subject,
                    'sentiment_type': sentiment_type
                })
        else:
            result.append({
                'predicate': original_predicates,
                'subject': subject,
                'sentiment_type': sentiment_type
            })

    return result


def categorize_entity(sentiment_reasons,tokens,entity_lexicon):
    """
    Categorize each reason record based on the subject token and entity lexicon (e.g., if subject lemma is "room", entity is "Room"). If there are multiple n_subjects, check the category for each n_subject and assign the most relevant category (e.g., if one of the n_subjects is "room", assign "Room" as the category). If no category can be assigned, assign "Uncategorized".

    Parameters
    ----------
    sentiment_reasons : list
            (各要素はdict.n_subject,predicateのindexリスト.
            e.g. [{'subject':[0],'subject_candidates':[0,2],'predicates':[3]},{'subject':[2],'subject_candidates':[0,2],'predicates':[3]}..]   
    tokens : list
             一投稿のtokenizer後(形態素解析後)のリスト(各要素はdict)
             [{{'sentiment':0,'index':0,'index_pertext':0,'lemma':'FNS','pos':'名詞',},{...},...]
    entity_lexicon: df
            DataFrame for grouping tokens into entities. It has two columns: 'term' and 'entity'. 'term' is the token lemma and 'entity' is the entity category (e.g., 'お風呂'→'Bathroom', 'シャワー'→'Bathroom').
 
    Returns
    -------
    None
    """


    # tokens を index → token の辞書に変換
    token_index_map = {
        token['index']: token
        for token in tokens
    }

    for item in sentiment_reasons:
        for i, sub_idx in enumerate(item['subject']):

            # tokens から該当 token を取得
            token = token_index_map.get(sub_idx)
            lemma = token.get('lemma')

            # get entity category from lexicon
            entity_category = entity_lexicon.loc[entity_lexicon['term'] == lemma, 'entity']

            if not entity_category.empty:
                item['entity'] = entity_category.values[0]
                break
            # end of loop
            if i == len(item['subject']) - 1:
                item['entity'] = None



def categorize_issue(sentiment_reasons,tokens,issue_lexicon):
    """
    Categorize each reason record based on the subject token and issue lexicon (e.g., if subject lemma is "room", issue is "Room"). If there are multiple n_subjects, check the category for each n_subject and assign the most relevant category (e.g., if one of the n_subjects is "room", assign "Room" as the category). If no category can be assigned, assign "Uncategorized".

    Parameters
    ----------
    sentiment_reasons : list
            (各要素はdict.n_subject,predicateのindexリスト.
            e.g. [{'subject':[0],'subject_candidates':[0,2],'predicates':[3]},{'subject':[2],'subject_candidates':[0,2],'predicates':[3]}..]   
    tokens : list
             一投稿のtokenizer後(形態素解析後)のリスト(各要素はdict)
             [{{'sentiment':0,'index':0,'index_pertext':0,'lemma':'FNS','pos':'名詞',},{...},...]
    issue_lexicon: df
            DataFrame for grouping tokens into issues. It has two columns: 'term' and 'issue_category'. 'term' is the token lemma and 'issue_category' is the issue category (e.g., '汚い'→'Cleanliness').
 
    Returns
    -------
    None
    """
    
    token_index_map = {
        token['index']: token
        for token in tokens
    }

    for item in sentiment_reasons:
        if len(item['predicate']) > 0 and item['predicate'][0] != 'None': # if there is a predicate
            token = token_index_map.get(item['predicate'][0])
            lemma = token.get('lemma')
            issue_category = issue_lexicon.loc[issue_lexicon['term'] == lemma, 'issue_category']
            if not issue_category.empty:
                item['issue_category'] = issue_category.values[0]
            else:                
                item['issue_category'] = None
        else:  
            item['issue_category'] = None


def caluclate_confidence(sentiment_reasons,tokens):


    # tokens を index → token の辞書に変換
    token_index_map = {
        token['index']: token
        for token in tokens
    }

    for item in sentiment_reasons:


        item['confidence'] = 1 # default

        # Uncategorized
        if item['entity'] == None:
            item['confidence'] -= 0.2

        if item['issue_category'] == None:
            item['confidence'] -= 0.2

        if item['subject'] == ['None'] or item['predicate'] == ['None']:
            item['confidence'] -= 0.3
        else:
            # distance between predicate and the nearest subject
            min_distance = min(abs(x - item['predicate'][0]) for x in item['subject'])
            item['confidence'] -= 0.03*(min_distance-1)

        if item['confidence'] < 0:
            item['confidence'] = 0  
        else:
            item['confidence'] = round(item['confidence'],2)


def index_to_words(sentiment_reasons,tokens):
    """
    subject,predicateのindexをtokensを元に単語(lemma)に変換
    Parameters
    ----------
    sentiment_reasons : list
            e.g. [{'subject':[0,1],'predicate':[3]},{'subject':[0,1],'predicate':[4]}..]
    -------
    None

    Example
    -------
    sentiment_reasons = [{'subject':[0,2],'predicate':[3], 'review_id':1}]
    tokens = [{'index':0,'lemma':'FNS','pos':'名詞'},{'index':1,'lemma':'は','pos':'助詞'},{'index':2,'lemma':'商品','pos':'名詞'},{'index':3,'lemma':'高い','pos':'形容詞'}]
    ↓
    sentiment_reasons = [{'subject':[FNS,商品],'predicate':'高い', 'review_id':1}]
    """ 

    token_index_map = {
        token['index']: token
        for token in tokens
    }

    for sentiment_reason in sentiment_reasons:
        for key in ['subject','predicate']:
            words_by_key = []
            for idx in sentiment_reason[key]:
                if idx == 'None':
                    continue
                words_by_key.append(token_index_map[idx]['lemma'])

            if key == 'predicate':
                if len(words_by_key) == 0:
                    words_by_key = None
                else:
                    words_by_key = words_by_key[0]  # convert list to string for predicate

            sentiment_reason[key] = words_by_key



def transform_reason_records(reason_records, processed_reviews, lexicons, args):

    transformed_reason_records = []
    for records_per_review, review in zip(reason_records, processed_reviews):



        # split reason predicates when there are multiple predicates
        records_per_review = split_reason_predicates(records_per_review)
        # remove duplicate reasons (if there are multiple identical subject-predicate pairs)
        records_per_review = remove_duplicate_reasons(records_per_review)
        # attach review_id, reason_id and run_id
        attach_reason_ids(records_per_review, review)

        # categorize reasons based on the tokens and lexicons
        categorize_entity(records_per_review,review["tokens"],lexicons['entity'])
        categorize_issue(records_per_review,review["tokens"],lexicons['issue'])

        # calulate confidence score for each reason record based on heuristics (e.g., if subject or predicate is None, if category is Uncategorized, distance between subject and predicate, etc.)
        caluclate_confidence(records_per_review,review["tokens"])
        #print("After adding category and confidence",records_per_review)
        # convert subject and predicate indices to words
        index_to_words(records_per_review,review["tokens"])

        transformed_reason_records.append(records_per_review)
        #reasons = enrich_reason_metadata(reasons, categories_lexicon)
        #reasons = index_reason_tokens(reasons)

    return transformed_reason_records

