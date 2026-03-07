import MeCab
import unicodedata
import neologdn
import pandas as pd
import re



def search_synonym_tokens(tokens, synonym_lexicon):
    """
    Search synonym words in tokens using synonym lexicon and update tokens with 'synonym' key

    Parameters
    ----------
    tokens : list of dict
        
    synonym_lexicon : dict
        list of dict (e.g. of negative [{'lemma':'俺', 'pos':'名詞', 'synonym':'私'}, ...])

    """

    for token in tokens:
        for syn in synonym_lexicon:
            if token['lemma'] == syn['lemma'] and token['pos'] == syn['pos']:
                token.update({'synonym': syn['synonym']})


# 文末判定用 正規表現コンパイル
TEXT_SEP_LIST=[
    r'!+', #0
    r'\?+', #1
    r'。+', #2
    r'、、+', #3
    r'\.\.\.+',#4
    r'・・・+',#5
    r'…+',#6
    r'[\(\)]',#7
    r'wwww+',#8
    r'\s+', #9
    r'\#+', #10
    # 顔文字
    r'(\(\)|\(\'\°\ω\°\`\*\)|\(_๑òωó\)_|\(\'・ω・\`\)|\(\';ω;\`\)|\(\'・Д・\`\)|_\:\(\'ཀ\`」∠\)\:|\(\'・_・\`\)|\_\(:3」∠\)\_|\(\'\、3_ヽ\)\_|\(。\-_\-。\)|\(\-。\-;\)|\( \'ω\'\)|\(p\'□\`q\)|\\\(^o^\)\/|\(\'Д\`\)|\(\^_\^;\)|\(‾▽‾;\))', #11
    r'[😉😁😂😃😄😅😆😇😈😉😊😋😌😍😎😏😐😑😒😓😔😕😖😗😘😙😚😛😜😝😞😟😠😡😢😣😤😥😦😧😨😩😪😫😬😭😮😯😰😱😲😳😴😵😶😷😸😹😺😻😼😽😾😿🙀🙁🙂🙃🙄🤐🤑🤒🤓]',#12
    # 絵文字
    r'[🙇‍🙏☔️🙋‍💦]',#13
    r'\|+', #14
]

TEXT_SEP_PATTERNS=[re.compile(d) for d in TEXT_SEP_LIST]

def normalize_text(text):
    
    """ 
    Normalize text for sentence separation by transforming the end of text to '|', normalizing text to NFKC, and unifying upper and lower case.

    Parameters
    ----------
    test : str

    Returns
    -------
    text : str
    """

    # Normalize text for sentence separation by transforming the end of text(e.g., '!', '?', '.', '...') to '|'
    for p in TEXT_SEP_PATTERNS:
        text = p.sub('|',text)

    # Normalize text to NFKC to reduce formatting inconsistencies
    # e.g. ＡＢＣ → ABC, １２３ → 123, ① → 1
    text = unicodedata.normalize('NFKC',text)#表記ゆれの統一
    # neologdn for normalizing some compatible kanji (e.g., 「髙」and 「高」) in japanese text
    text = neologdn.normalize(text)
    # unify upper and lower case
    text = text.lower() 
    
    return text


def tokenize(text, search_text)->list:
    """ 
    Morphological Analysis by MeCab (japanese text), adding extra informations as, index of word, text_no in which word belongs,
    and start/end position of word in original text using search_text, and return list of dict with these informations.
    
    parameters
        text:str
            Normalized text for morphological analysis.
        search_text:str
            Original text for searching word position in text. This is required because normalized text is different from original text and cannot be used to search word position in original text.
    return
        list of dict
            ex[{'index':0,'index_pertext':0,'lemma':'FNS','pos':'名詞','sub_pos':'固有名詞','text_no':1,'inflection':'*','surface':'fns',...},
            {'index':1,'index_pertext':1,'lemma':'に','pos':'助詞','sub_pos':'格助詞','text_no':1,'inflection':'*','surface':'に',...},
            ...]
    """

    # load MeCab Tagger
    tagger = MeCab.Tagger()
    
    node = tagger.parseToNode(text)
    

    w_surfaces=[] # 表層形
    w_poses=[] # 品詞
    w_sub_poses=[] # 品詞細分類1
    w_inflections=[]
    w_lemmas=[] # 原形
    w_starts=[]
    w_ends=[]
    search_from=0 # 原文内の単語開始・終了位置の検索開始位置
    # 単語ごとに各情報を辞書に格納

    while node:

        features = node.feature.split(',')
        if features[0] != 'BOS/EOS':

# 句構成------------------------------------            
            # 動詞(自立)＋れる/られる/せる/させる
            if len(w_lemmas)>0 and features[0]=='動詞' and features[1]=='接尾'\
                    and features[6] in ['られる','れる','せる','させる']\
                    and len(w_lemmas)!=0 and w_poses[-1]=='動詞'\
                    and w_inflections[-1] in ['未然形','未然レル接続']:# 未然レル→サ変＋させる等
                        
                # 直前の原形
                w_lemmas[-1]=w_surfaces[-1]+features[6]

                ### 表層形,原形以外の情報は一旦変更しない
                w_surfaces[-1]=w_surfaces[-1]+node.surface
                w_inflections[-1]=features[5]
                w_ends[-1]=w_ends[-1]+len(node.surface)
                
            # 打消しor希望助動詞で直前が自立動詞/形容詞の場合のみ、助動詞を加えた形に変更
            elif len(w_lemmas)>0 and features[0]=='助動詞' and features[6] in ['ない','ぬ','たい','へん']\
                    and len(w_lemmas)!=0\
                    and w_poses[-1] in ['動詞','形容詞']\
                    and w_inflections[-1] in ['未然形','連用テ接続','連用形']:# 連用テ接続→形容詞(美しく+ない)
                        
                        
                # 直前の原形 ← 直前の表層形+['ない','たい']に変更 e.g.'行きたい'

                if features[6] in ['ない','ぬ','へん']:
                    w_lemmas[-1]=w_surfaces[-1]+'ない'
                    w_inflections[-1]='否定形'
                elif features[6]=='たい':
                    w_lemmas[-1]=w_surfaces[-1]+'たい'
                    w_inflections[-1]='希望形'
                    

                # 直前の表層形 ← 直前の表層形+['ない','たい']表層形に変更 e.g.'行きたく'.
                ## '行きたくない'等 たい,ないが続く場合に必要
                ### 表層形,原形以外の情報は一旦変更しない

                w_surfaces[-1]=w_surfaces[-1]+node.surface
                w_ends[-1]=w_ends[-1]+len(node.surface)

                
            # 動詞+動詞(てる/いる) 食べてる
            elif len(w_lemmas)>0 and features[0]=='動詞' and features[1]=='非自立'\
                    and features[6] in ['てる','いる']\
                    and len(w_lemmas)!=0\
                    and w_poses[-1] == '動詞'\
                    and w_inflections[-1] in ['連用形','連用形+接続助詞','連用タ接続']:
                        
                # 原形は書き換えない(書き換えると'食べる'と'食べて'が別動詞になる)
                
                
                w_surfaces[-1]=w_surfaces[-1]+node.surface
                w_inflections[-1]=features[5]
                #print('AAA',w_ends[-1],type(w_ends[-1]))
                w_ends[-1]=w_ends[-1]+len(node.surface)
                
            # 動詞+接続助詞'て'+動詞'いる'　食べている
            elif len(w_lemmas)>0 and features[0]=='助詞' and features[1]=='接続助詞'\
                    and features[6]=='て'\
                    and len(w_lemmas)!=0\
                    and w_poses[-1] == '動詞'\
                    and w_inflections[-1] in ['連用形','連用タ接続']:
                        
                # 直前の原形
                #w_lemmas[-1]=w_surfaces[-1]+features[6]

                # 直前の表層形 ← 直前の表層形+['ない','たい']表層形に変更 e.g.'行きたく'.
                ## '行きたくない'等 たい,ないが続く場合に必要
                ### 表層形,原形以外の情報は一旦変更しない
                w_surfaces[-1]=w_surfaces[-1]+node.surface
                w_inflections[-1]=w_inflections[-1]+'+接続助詞'
                #print(node.surface)
                #print(w_lemmas[-1])
                
                w_ends[-1]=w_ends[-1]+len(node.surface)
                
#------------                
            # サ変接続＋する＝動詞
            elif len(w_lemmas)>0 and features[0]=='動詞' and features[6] in ['する','できる','出来る']\
                    and len(w_lemmas)!=0 and w_sub_poses[-1] in ['サ変接続']:
                        
                # 直前の原形 ← 直前の表層形+['する']に変更 e.g.'転売する'
                w_lemmas[-1]=w_surfaces[-1]+features[6]
                    
                # 表層形と共に品詞、活用形を継承（転売＋しない/して等に対応するため）
                w_surfaces[-1]=w_surfaces[-1]+node.surface
                w_poses[-1]='動詞'
                w_inflections[-1]=features[5]# 活用形
                w_ends[-1]=w_ends[-1]+len(node.surface)

            # サ変接続＋助詞＋する＝動詞
            elif len(w_lemmas)>1 and features[0]=='動詞' and features[6] in ['する','できる','出来る']\
                    and len(w_lemmas)!=0 and w_poses[-1]=='助詞'\
                        and w_sub_poses[-2]=='サ変接続':
                        
                # 直前の原形 
                ## 助詞は除外する
                w_lemmas[-2]=w_lemmas[-2]+features[6]
                    
                # 表層形、品詞を動詞に変更
                w_surfaces[-2]=w_surfaces[-2]+node.surface
                w_poses[-2]='動詞'
                w_inflections[-2]=features[5]
                w_ends[-2]=w_ends[-2]+len(w_surfaces[-1])+len(node.surface)

                w_surfaces.pop() # 表層形
                w_poses.pop() # 品詞
                w_sub_poses.pop() # 品詞細分類
                w_lemmas.pop() # 原形
                w_inflections.pop()
                w_starts.pop()
                w_ends.pop()

            # 上記助動詞を除いた全品詞の単語情報を格納
            else:

                w_surfaces.append(node.surface)
                w_poses.append(features[0])
                w_sub_poses.append(features[1])
                w_lemmas.append(features[6] if features[6]!='*' else node.surface)
                w_inflections.append(features[5])


                try: #前処理前のテキストから検索
                    w_starts.append(search_from + search_text[search_from:].index(node.surface.lower()))

                except ValueError as e: # 見つからない場合('|',絵文字等は前処理によって見つからない)
                    '''
                    print(e)
                    print('text:',text)
                    print('node.surface:',node.surface)
                    '''
                    if len(w_ends) > 0:
                        w_starts.append(w_ends[-1] + 1) # 先頭(前単語の直後)にあるとして、表層形の文字分先に進める
                    else:# 文頭
                        w_starts.append(0)

                finally:
                    w_ends.append(w_starts[-1]+len(node.surface)-1)
                    search_from = w_ends[-1] + 1


        node = node.next      


    # text_no、文ごとのindex記載-----
    sentence_nos=[] # 文No.
    indexes_pertext=[]
    i=1
    j=0 #文ごとのindex　0から振る
    for w_surface,w_class,class_detail,org,w_katsu in zip(w_surfaces,w_poses,w_sub_poses,w_lemmas,w_inflections):
        if w_class=='記号' and w_surface=='|': #終末記号ごとにNo.記載
            sentence_nos.append("-")
            indexes_pertext.append("-")
            i=i+1 # text_no
            j=0 # 文ごとのindexリセット
        elif w_class not in ['名詞','動詞','形容詞','形容動詞','連体詞','接頭詞','助詞','助動詞','記号']: ##特定品詞除外
            sentence_nos.append("-")
            indexes_pertext.append("-")
        else:
            sentence_nos.append(i)
            indexes_pertext.append(j)
            j=j+1
            
## keyと取得したvalueから辞書型に変換
    d=[] 
    i=0
    #print('原形',w_lemmas)
    #print('a',w_starts)
    keys=['index','index_pertext','surface','pos','sub_pos','lemma','inflection','text_no','sentiment','synonym','start_offset','end_offset','text_highlighted']
    for index_pertext,w_surface,w_class,w_class_detail,w_katsu,w_org,sen_no,w_start,w_end in zip(indexes_pertext,w_surfaces,w_poses,w_sub_poses,w_inflections,w_lemmas,sentence_nos,w_starts,w_ends):
        if w_class=='記号' and w_surface=='|':
            pass
        elif w_class in ['名詞','動詞','形容詞','形容動詞','連体詞','接頭詞','助詞','助動詞','記号']:
            values=[i,index_pertext,w_surface,w_class,w_class_detail,w_org,w_katsu,sen_no,0,'',w_start,w_end,''] # w_index_pertext,sentimentは一旦全て0,synonymもすべて空白設定
            d.append(dict(zip(keys,values)))
            i=i+1


    return d


def search_sentiment_tokens(tokens, sentiment_lexicon, args):
    """
    search negative or positive words in tokens using sentiment lexicon and update tokens with 'sentiment' key (1 if negative word, 0 if not)

    Parameters
    ----------
    tokens : list of dict
        
    sentiment_lexicon : df
        e.g.
        dataframe([{'term':悪い,'polarity':negative,'language':ja},...])
    args: argparse.Namespace

    """

    target_sentiment_lexicon = sentiment_lexicon[sentiment_lexicon['polarity'] == args.sentiment]
    # create dict with term as key and sentiment as value for faster search
    sentiment_map = target_sentiment_lexicon.set_index('term')['polarity'].to_dict()

    # check if lemma of token is in sentiment_lexicon and update sentiment label to tokens
    for token in tokens:
        lemma = token.get('lemma')
        if lemma in sentiment_map:
            token['sentiment'] = sentiment_map[lemma]
        else:
            token['sentiment'] = None


    # for token in tokens:
    #     if token['lemma'] in sentiment_lexicon:
    #         token.update({'sentiment': 1})


def preprocess_reviews(valid_reviews, lexicons, args):
    """
    Preprocess reviews by normalizing text, tokenizing, and searching tokens with sentiment and synonyms.

    Parameters
    ----------
    valid_reviews : list of dict
        list of valid reviews
    lexicons : dict
        dict of lexicons including 'sentiment', 'category'

    Returns
    -------
    list of dict
        list of reviews with added 'tokens' key which is a list of dict with token information (e.g. [{'index':0,'index_pertext':0,'lemma':'FNS','pos':'名詞','sub_pos':'固有名詞','text_no':1,'inflection':'*','surface':'fns','sentiment':0,'synonym':'',...}, ...])
    """


    for review in valid_reviews:

        # normalize text for tokanization
        normalized_text = normalize_text(review['review_text'])

        # tokenization and morphological analysis.
        ## the original text(the 2nd parameter) is required to find the position of words in the text
        tokens = tokenize(normalized_text, review['review_text'].lower()) 

        # search sentiment tokens by sentiment_lexicon and update sentiment label to tokens
        search_sentiment_tokens(tokens, lexicons['sentiment'],args)

        # TODO search synonym tokens by synonym_lexicon and update synonym label to tokens
        #search_synonym_tokens(tokens, lexicons['synonym'])

        review.update({'tokens': tokens})

    return valid_reviews