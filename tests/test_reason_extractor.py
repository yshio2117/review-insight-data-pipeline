import pytest

from src.reason_extraction.extraction.reason_extractor import extract_reason_subjects, extract_reason_predicates, extract_reason_pairs


# -----------------------
# extract_reason_subjects tests
# -----------------------

def test_extract_reason_subjects_false():
    """test with search_from_end=False（search to the beginning of the sentence from the index"""
    
    # test sentence: 「高い料金に怒る」(Be angry about the high price)
    sentiment_sentence = [
        {'index': 0, 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '高い', 'inflection': '*'},
        {'index': 1, 'pos': '名詞', 'sub_pos': '一般', 'lemma': '料金', 'inflection': '*'},
        {'index': 2, 'pos': '助詞', 'sub_pos': '格助詞', 'lemma': 'に', 'inflection': '*'},
        {'index': 3, 'pos': '動詞', 'sub_pos': '自立', 'lemma': '怒る', 'inflection': '*'}
    ]
    
    ext_subjects = []
    ext_lemmas = []
    
    # from index=3(怒る) 
    extract_reason_subjects(
        search_from_end=False,
        sentiment_sentence=sentiment_sentence,
        start_index=3,
        ext_subjects_in_sentence=ext_subjects,
        ext_subject_lemmas=ext_lemmas
    )
    
    # check if the Noun '料金' before the verb '怒る' will be extracted
    assert ext_subjects == [1]
    assert ext_lemmas == ['料金']


def test_extract_reason_subjects_true():
    """test with search_from_end=True（search to the end of the sentence from the index and stop when verb/adj is found"""
    
    # テスト文: 「デザインが悪い画面も」
    sentiment_sentence = [
        {'index': 0, 'pos': '名詞', 'sub_pos': '一般', 'lemma': 'デザイン', 'inflection': '*'},
        {'index': 1, 'pos': '助詞', 'sub_pos': '格助詞', 'lemma': 'が', 'inflection': '*'},
        {'index': 2, 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '悪い', 'inflection': '*'},
        {'index': 3, 'pos': '名詞', 'sub_pos': '一般', 'lemma': '画面', 'inflection': '*'},
        {'index': 4, 'pos': '助詞', 'sub_pos': '係助詞', 'lemma': 'も', 'inflection': '*'}
    ]
    
    ext_subjects = []
    ext_lemmas = []
    
    # search form the end of the sentence and stop when verb/adj is found (index=2)
    extract_reason_subjects(
        search_from_end=True,
        sentiment_sentence=sentiment_sentence,
        start_index=2, # this will be ignored when search_from_end=True
        ext_subjects_in_sentence=ext_subjects,
        ext_subject_lemmas=ext_lemmas
    )
    
    # It should extract the noun '画面' and break at verb '悪い'. ('デザイン' should not be extracted)
    assert ext_subjects == [3]
    assert ext_lemmas == ['画面']


# -----------------------
# extract_reason_predicates tests
# -----------------------

def test_extract_reason_predicates_false():
    """test with search_backward=False (search to the end of the sentence)"""
    
    # test sentence: 「とても良いホテルだ」(very good hotel)
    sentiment_sentence = [
        {'index': 0, 'pos': '副詞', 'sub_pos': '一般', 'lemma': 'とても', 'inflection': '*'},
        {'index': 1, 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '良い', 'inflection': '*'},
        {'index': 2, 'pos': '名詞', 'sub_pos': '一般', 'lemma': 'ホテル', 'inflection': '*'},
        {'index': 3, 'pos': '助動詞', 'sub_pos': '*', 'lemma': 'だ', 'inflection': '*'}
    ]
    
    ext_idx = []
    ext_lemmas = []
    ext_tmp = [] # tmp storage
    
    # search from index=0(とても) to the end of text
    extract_reason_predicates(
        search_backward=False,
        sentiment_sentence=sentiment_sentence,
        start_index=0,
        ext_predicates_in_sentence=ext_idx,
        ext_predicate_lemmas=ext_lemmas,
        ext_predicate_lemmas_tmp=ext_tmp
    )

    # extract '良い'(adj) and break at 'ホテル'(noun)   
    assert ext_idx == [1]
    assert ext_lemmas == ['良い']


def test_extract_reason_predicates_true():
    """test with search_backward=True (search to the beginning of the sentence)"""
    
    # test sentence 「料金が高くて怒る」(Be angry about the high price)
    sentiment_sentence = [
        {'index': 0, 'pos': '名詞', 'sub_pos': '一般', 'lemma': '料金', 'inflection': '*'},
        {'index': 1, 'pos': '助詞', 'sub_pos': '格助詞', 'lemma': 'が', 'inflection': '*'},
        {'index': 2, 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '高い', 'inflection': '*'},
        {'index': 3, 'pos': '助詞', 'sub_pos': '接続助詞', 'lemma': 'て', 'inflection': '*'},
        {'index': 4, 'pos': '動詞', 'sub_pos': '自立', 'lemma': '怒る', 'inflection': '*'}
    ]
    
    ext_idx = []
    ext_lemmas = []
    ext_tmp = []
    
    # search from index=4(怒る) to the beginning of the sentence
    extract_reason_predicates(
        search_backward=True,
        sentiment_sentence=sentiment_sentence,
        start_index=4,
        ext_predicates_in_sentence=ext_idx,
        ext_predicate_lemmas=ext_lemmas,
        ext_predicate_lemmas_tmp=ext_tmp
    )
    
    # it should extract '怒る'(verb), '高い'(adj), then break at '料金'(noun)
    # the order of indice will be reverced in the end. The result has to be ['高い','怒る']
    assert ext_idx == [2, 4]
    assert ext_lemmas == ['高い', '怒る']



# -----------------------
# extract_reason_pairs tests
# -----------------------

def test_extract_reason_pairs_noun_sentiment():
    """ Test when the polarity term is a Noun"""
    
    # test sentence: 「部屋が汚い」(the room is dirty) （negative term: 汚い(dirty）
    tokens = [
        {'sentiment': None, 'index': 0, 'index_pertext': 0, 'text_no': 1, 'surface': '部屋', 'pos': '名詞', 'sub_pos': '一般', 'lemma': '部屋', 'inflection': '*'},
        {'sentiment': None, 'index': 1, 'index_pertext': 1, 'text_no': 1, 'surface': 'が',   'pos': '助詞', 'sub_pos': '格助詞', 'lemma': 'が', 'inflection': '*'},
        {'sentiment': 'negative','index': 2, 'index_pertext': 2, 'text_no': 1, 'surface': '汚い', 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '汚い', 'inflection': '*'}
    ]
    
    result = extract_reason_pairs(tokens)
    
    # just one pair should be extracted
    assert len(result) == 1
    
    pair = result[0]
    assert pair['sentiment_type'] == 'negative'
    assert pair['subject'] == [0]    # index 0: 部屋
    assert pair['predicates'] == [2] # index 2: 汚い


def test_extract_reason_pairs_adj_sentiment():
    """Test when the polarity term is an Adjective"""
    
    # test sentence:「料理が美味しい」(the dish is delicious) （美味しい：positive）
    tokens = [
        {'sentiment': None,       'index': 0, 'index_pertext': 0, 'text_no': 1, 'surface': '料理',     'pos': '名詞', 'sub_pos': '一般', 'lemma': '料理', 'inflection': '*'},
        {'sentiment': None,       'index': 1, 'index_pertext': 1, 'text_no': 1, 'surface': 'が',       'pos': '助詞', 'sub_pos': '格助詞', 'lemma': 'が', 'inflection': '*'},
        {'sentiment': 'positive', 'index': 2, 'index_pertext': 2, 'text_no': 1, 'surface': '美味しい', 'pos': '形容詞', 'sub_pos': '自立', 'lemma': '美味しい', 'inflection': '*'}
    ]
    
    result = extract_reason_pairs(tokens)
    
    # just one pair should be extracted
    assert len(result) == 1
    
    pair = result[0]
    assert pair['sentiment_type'] == 'positive'
    assert pair['subject'] == [0]    # index 0: 料理
    assert pair['predicates'] == [2] # index 2: 美味しい
