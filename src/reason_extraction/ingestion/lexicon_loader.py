import csv
from config.settings import BASE_DIR
import pandas as pd


def read_sentiment_lexicon():
    """
    read sentiment lexicon(negative/positive) from local csv file

    Parameters
    ----------
    sentiment: char
        negative or positive. 

    Returns
    -------
    sentiment_lexicon: pd.DataFrame
        sentiment lexicon dataframe with columns 'term','polarity' and 'language'
    """


    sentiment_lexicon = pd.read_csv(BASE_DIR / "dics/sentiment_lexicon.csv", encoding="utf_8")
    
    return sentiment_lexicon


def read_entity_lexicon():
    """
    read entity lexicon from local csv file
    """

    df = pd.read_csv(BASE_DIR / "dics/entity_lexicon.csv")
    return df


def read_issue_lexicon():
    """
    read issue lexicon from local csv file
    """

    df = pd.read_csv(BASE_DIR / "dics/issue_lexicon.csv")
    return df


def read_lexicons():
    """
    Read all lexicons (sentiment, entity, and issue) and return as dict

    Parameters
    ----------
        None
        
    Returns
    -------
    lexicons: dict
        dict of all lexicons with keys 'sentiment', 'entity', 'issue'
    """
    

    lexicons = {
        'sentiment': read_sentiment_lexicon(),
        'entity': read_entity_lexicon(),
        'issue': read_issue_lexicon()
    }

    return lexicons