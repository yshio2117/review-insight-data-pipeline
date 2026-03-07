import pytest
import pandas as pd
import argparse
from src.reason_extraction.preprocessing.review_preprocessor import normalize_text, tokenize, search_sentiment_tokens

# -----------------------
# normalize_text tests
# -----------------------

@pytest.mark.parametrize(
    "inp, expected",
    [
        # 1) check lower()
        ("HELLO", "hello"),

        # 2) check punctuation and ellipsis replacement to "|"
        ("おもしろ!!!", "おもしろ|"),
        ("まじ??", "まじ|"),
        ("最悪。", "最悪|"),
        ("やば...", "やば|"),
        ("え…", "え|"),

        # 3) (\s+) to |
        ("あの   それから", "あの|それから"),
        ("あ\tい\nう", "あ|い|う"),

        # 4) wwww+ to | 
        ("うけるwwww", "うける|"),

        # 5) # to | 
        ("#hashtag", "|hashtag"),

        # 6) (\(|\)) to |
        ("(そうですか)", "|そうですか|"),

        # 7) emojis to | 
        ("いいね😂だめだよ", "いいね|だめだよ"),

        # 8) consecutive delimiters collapse into a single |
        ("すごい!!!  本当??", "すごい|本当|"),
    ]
)
def test_normalize_text_basic(inp, expected):
    assert normalize_text(inp) == expected


def test_normalize_text_nfkc_fullwidth_to_halfwidth():
    # NFKC: 全角英数字が半角になる
    assert normalize_text("ＡＢＣ１２３") == "abc123"


def test_normalize_text_is_idempotent():
    # check idempotency
    s = "すごい!!!  ＡＢＣ１２３😂"
    assert normalize_text(normalize_text(s)) == normalize_text(s)


# -----------------------
# Tokenize tests
# TODO: currently the test is dependent on MeCab and it may be not good because the result may change depending on the dictionary and os
# -----------------------

def test_tokenize_basic():
    """ test for basic tokenization and character offsets"""

    search_text = "私は走る".lower()
    text = normalize_text(search_text)
    tokens = tokenize(text, search_text)
    
    # tokens expected ("私" / "は" / "走る")
    assert len(tokens) == 3
    
    # first word: 私
    assert tokens[0]['surface'] == '私'
    assert tokens[0]['pos'] == '名詞'
    assert tokens[0]['start_offset'] == 0
    assert tokens[0]['end_offset'] == 0 # len("私")-1 = 0
    
    # second word: は
    assert tokens[1]['surface'] == 'は'
    assert tokens[1]['pos'] == '助詞'
    assert tokens[1]['start_offset'] == 1
    assert tokens[1]['end_offset'] == 1 # len("は")-1 = 0 => start(1)+0=1
    
    # the 3rd word: 走る
    assert tokens[2]['surface'] == '走る'
    assert tokens[2]['pos'] == '動詞'
    assert tokens[2]['start_offset'] == 2
    assert tokens[2]['end_offset'] == 3 # len("走る")-1 = 1 => start(2)+1=3


def test_tokenize_sahen_suru():
    """ test for "サ変接続＋する" being combined into a single verb token"""

    search_text = "販売する".lower()
    text = normalize_text(search_text)

    tokens = tokenize(text, search_text)
    
    # "販売" + "する" will be combined into a single token "販売する"
    assert len(tokens) == 1
    assert tokens[0]['surface'] == '販売する'
    assert tokens[0]['pos'] == '動詞'
    assert tokens[0]['lemma'] == '販売する'
    assert tokens[0]['start_offset'] == 0
    assert tokens[0]['end_offset'] == 3 # "販売する"の4文字なので 0〜3


def test_tokenize_verb_tai():
    """ test for "動詞＋希望助動詞(たい)" being combined into a single verb token"""

    search_text = "行きたい".lower()
    text = normalize_text(search_text)
    tokens = tokenize(text, search_text)
    
    # "行き"(行く) と "たい"  will be combined into a single token "行きたい"
    assert len(tokens) == 1
    assert tokens[0]['surface'] == '行きたい'
    assert tokens[0]['pos'] == '動詞'
    assert tokens[0]['lemma'] == '行きたい'
    assert tokens[0]['inflection'] == '希望形'

def test_tokenize_verb_nai():
    """ test for "動詞＋打消助動詞(ない)" being combined into a single verb token"""

    search_text = "食べない".lower()
    text = normalize_text(search_text)
    tokens = tokenize(text, search_text)
    
    # "食べ"(食べる) と "ない"  will be combined into a single token "食べない"
    assert len(tokens) == 1
    assert tokens[0]['surface'] == '食べない'
    assert tokens[0]['pos'] == '動詞'
    assert tokens[0]['lemma'] == '食べない'
    assert tokens[0]['inflection'] == '否定形'


# -----------------------
# search_sentiment_tokens tests
# -----------------------

@pytest.fixture
def sample_sentiment_lexicon():
    """fixture for a sample sentiment lexicon DataFrame"""

    data = {
        'term': ['あがく', 'あきらめる', '喜ぶ', '素晴らしい'],
        'polarity': ['negative', 'negative', 'positive', 'positive'],
        'language': ['ja', 'ja', 'ja', 'ja']
    }
    return pd.DataFrame(data)


def test_search_sentiment_tokens_negative(sample_sentiment_lexicon):
    """Test when args.sentiment is 'negative'"""
    
    # test tokens
    tokens = [
        {'lemma': 'あきらめる'},  # negative
        {'lemma': '喜ぶ'},      # positive
        {'lemma': '歩く'},      # not in lexicon
    ]
    
    # create a Mock args with sentiment = 'negative'
    args = argparse.Namespace(sentiment='negative')
    
    search_sentiment_tokens(tokens, sample_sentiment_lexicon, args)
    
    # only negative word should be marked, others should be None
    assert tokens[0]['sentiment'] == 'negative'
    assert tokens[1]['sentiment'] is None
    assert tokens[2]['sentiment'] is None


def test_search_sentiment_tokens_positive(sample_sentiment_lexicon):
    """Test when args.sentiment is 'positive'"""
    
    tokens = [
        {'lemma': 'あきらめる', 'sentiment': 0},
        {'lemma': '素晴らしい', 'sentiment': 0},
    ]
    
    # create a Mock args with sentiment = 'positive'
    args = argparse.Namespace(sentiment='positive')
    
    # execute
    search_sentiment_tokens(tokens, sample_sentiment_lexicon, args)
    
    # only positive word should be marked, others should be None
    assert tokens[0]['sentiment'] is None
    assert tokens[1]['sentiment'] == 'positive'


def test_search_sentiment_tokens_empty_list(sample_sentiment_lexicon):
    """Test when the token list is empty"""
    
    tokens = []
    args = argparse.Namespace(sentiment='negative')
    
    # check no error occurs
    search_sentiment_tokens(tokens, sample_sentiment_lexicon, args)
    assert len(tokens) == 0