import csv
import copy
from pathlib import Path


def extract_reason_subjects(conn_reverse,
             sentiment_text,
             search_from,
             subject_by_sentiment,
             subject_lemmas_by_sentiment,
             ):
    """
    n_subjectの検索(sentimentが属する文内)

    Parameters
    ----------
    conn_reverse : int
        0:n単語から前方に名詞検索, 1:文末から前方に名詞検索.
    sentiment_text : list
        n単語が属する文 ex[{'sentiment':0,'index':0,'index_pertext':0,'lemma':'FNS',},{...},..]
    search_from : int
        検索開始位置(sentiment_text内のindex).
    subject_by_sentiment : list
        検索済み主語のindex.        
    subject_lemmas_by_sentiment : list
        検索済み主語の原形.

    Returns
    -------
    subject_by_sentiment,subject_lemmas_by_sentiment.

    """


    # 検索範囲指定 n単語から前方に検索 or 文末から前方に検索
    ## N単語自身も検索対象に含む
    search_range = search_from+1 if conn_reverse==0 else len(sentiment_text)
    
    sp_particle = 0 # 特定助詞フラグ（1の間は動詞/形容詞/形容動詞を検索終了条件としない）
    # 該当する名詞がある限り検索
    for index_pertext in reversed(range(0,search_range)):

        # 名詞が繰り返す限り取得.主語不可名詞は除く('非自立'等)
        if sentiment_text[index_pertext]['pos']=='名詞' and sentiment_text[index_pertext]['sub_pos'] not in ['非自立','副詞可能','接尾','代名詞','特殊','数']:
            if sentiment_text[index_pertext]['lemma'] not in ['ー','人','人達','者','子','方','やつ','奴','こと','事']: # 長音記号(名詞,一般),mecab上接尾とならない名詞も主語不可(解析結果を接尾に修正してもよい. 
                subject_by_sentiment.append((sentiment_text[index_pertext]['index'])) #元のindex番号を主語として保存
                subject_lemmas_by_sentiment.append(sentiment_text[index_pertext]['lemma'])
                sp_particle=0
                            
        # 読点等はスキップして次へ
        #elif sentiment_text[index_pertext]['pos']=='記号' and sentiment_text[index_pertext]['sub_pos'] in ['読点','括弧閉','括弧開','一般']: # 読点等はスキップ
        #    continue
        
    # 主語前　名詞+動詞/形容詞/形容動詞+特定助詞は主語として取得(規則7)
        elif len(subject_by_sentiment)>0 and ((sentiment_text[index_pertext]['pos']=='助詞' and sentiment_text[index_pertext]['lemma'] in 
                                                                            ['けど','のに','から','て','ば'])\
                             # 規則8 仮定形助動詞も同様の扱い
                          or (sentiment_text[index_pertext]['pos']=='助動詞' and sentiment_text[index_pertext]['inflection'] == '仮定形')):
            sp_particle=1
            continue
        # 特定助詞条件で非主語名詞が来た場合検索条件終了
        elif sp_particle == 1 and sentiment_text[index_pertext]['pos'] in ['名詞']\
                              and sentiment_text[index_pertext]['lemma'] not in ['ん']: # 非自立名詞'ん'は例外でスキップ
            sp_particle=0


        # 動詞,形容詞,形容動詞,が続いたら検索ストップ(すでにn_subjectが取得された場合のみ)        
        elif sp_particle == 0 and len(subject_by_sentiment)>0 and sentiment_text[index_pertext]['pos'] in ['動詞','形容詞','形容動詞']:
            break 

        
    subject_by_sentiment.reverse()# 逆から取得しているので逆順に
    subject_lemmas_by_sentiment.reverse()    
    

    
def extract_reason_predicates(search_reverse,
             sentiment_text,
             search_from,
             predicate_by_sentiment,
             predicate_lemmas_by_sentiment,
             predicate_lemmas_by_sent_tmp
             ):
    """
    n_predicateの検索(sentimentが属する文内)

    Parameters
    ----------
    search_reverse : int
        0:n単語から後方へ検索, 1:n単語から前方へ検索.(n単語自身も検索対象)
    sentiment_text : list
        n単語が属する文 ex[{'sentiment':0,'index':0,'index_pertext':0,'lemma':'FNS',},{...},..]
    search_from : int
        検索開始位置(sentiment_text内のindex).
    predicate_by_sentiment : list
        検索済み述語のindex.        
    predicate_lemmas_by_sentiment : list
        検索済み述語の原形.
    predicate_lemmas_by_sent_tmp : list
        検索済み述語の原形一時保存.(文の結合があった場合)

    Returns
    -------
    predicate_by_sentiment,predicate_lemmas_by_sentiment.

    """
    
                
    num_before=len(predicate_by_sentiment) # 該当述語があるか判定用
    
    # 検索範囲指定            
    if search_reverse==1:# n単語から前方に述語検索
        search_range=reversed(range(0,search_from+1))
    elif search_reverse==0:# n単語から文末まで述語検索
        search_range = range(search_from,len(sentiment_text)) 
        
    
    # 述語が繰り返す限り取得
    for index_pertext in search_range:
        # 述語になり得る動詞,形容詞,形容動詞であれば保存(述語に関しては重複はすべて除く)
        if  sentiment_text[index_pertext]['pos'] in ['動詞','形容詞','形容動詞'] and (sentiment_text[index_pertext]['lemma'] not in predicate_lemmas_by_sentiment
                                                          and sentiment_text[index_pertext]['lemma'] not in predicate_lemmas_by_sent_tmp): # 重複は除外（述語のみ)
            #if sentiment_text[index_pertext]['sub_pos']=="非自立" and sentiment_text[index_pertext]['lemma'] in ["過ぎる","すぎる"]:
            #if sentiment_text[index_pertext]['sub_pos'] not in ["自立","形容動詞語幹","サ変接続"]:
            if sentiment_text[index_pertext]['sub_pos'] in ["非自立","接尾"] or sentiment_text[index_pertext]['lemma'] in ["過ぎる","すぎる"]:    
                continue # V+過ぎるは一旦全除外
                
                
            predicate_by_sentiment.append(sentiment_text[index_pertext]['index'])# 文章におけるindexを保存(文におけるindexではない)
            predicate_lemmas_by_sentiment.append(sentiment_text[index_pertext]['lemma'])# 原形も保存
            
        # 主語になりえる単語(自立名詞等)があればそこで検索ストップ
        elif ((len(predicate_by_sentiment)>0 or len(predicate_lemmas_by_sent_tmp)>0) and 
              sentiment_text[index_pertext]['pos'] in ['名詞'] and 
              sentiment_text[index_pertext]['sub_pos'] not in ['非自立','副詞可能','接尾','代名詞','特殊','数'] and
              sentiment_text[index_pertext]['lemma'] not in ['ー','人','人達','者','子','方','やつ','奴','こと','事']):
            break
        
    if num_before<len(predicate_by_sentiment) and search_reverse==1:# 逆から取得しているので逆順に並び変え（該当述語があった場合)       
        predicate_by_sentiment.reverse()
        predicate_lemmas_by_sentiment.reverse()
    


def extract_reason_pairs(tokens):
    """
    Extract negative(or positive) subjects and predicates from tokens based on rules defined in the paper.

    Parameters
    ----------
    tokens : list of dict. Each dict corresponds to a token after morphological analysis (tokenizer) for a single review.
             e.g. [{{'sentiment':0,'index':0,'index_pertext':0,'lemma':'FNS','pos':'名詞',},{...},...]

    Returns
    -------
    sentiment_reasons : list
            list of dict. subject and predicate pairs with sentiment label for a single review (multiple pairs for a single review can be extracted).
              e.g. [{'subject':[0],'predicates':[3],'sentiment':'negative'},{'subject':[0,2],'predicates':[1,3],'sentiment':'negative'}..]

    """
    
    
    
    subjects_by_sentiment=[]# 投稿内の全n_subject
    predicates_by_sentiment=[]# 投稿内の全n_predicate
    subject_by_sentiment=[]# n単語ごとのn_subject
    predicate_by_sentiment=[]# n単語ごとのn_predicate
    polarity_by_sentiment=[] # 検索する極性単語の極性(positive/negative)
    predicate_lemmas_by_sentiment=[]# n_predicate重複チェック用に原形を入れる(現状は原形で重複チェック)
    subject_lemmas_by_sentiment=[]
    #n_sentences=[]# (未使用) 規則6 n_subject,n_predicateの重複除外用[(n_subject1,n_predicate1),(n_subject2,n_predicate2),...)
    predicate_by_sent_tmp=[]# 文結合後の単語の順番保持用に一時保存させる.並び変え後predicate_by_sentimentに移動する
    predicate_lemmas_by_sent_tmp=[]
    conn_reverse=0 #文後方結合フラグ(前方に結合する場合0,後方に結合する場合1)
    polarity_idxs=[] #極性単語のindice
    max_text_no=1 #最大のtext_no

    
    # n単語のindex,投稿の最大のtext_no取得
    for token in tokens:
        if token['sentiment'] is not None: # positive or negative
            polarity_idxs.append((token['index'],token['sentiment']))
        if token['text_no']>max_text_no:
            max_text_no=token['text_no']
            
    text_num = max_text_no # 投稿内の文の数    


    #n単語のindexごとにn_subject,predicateの検索
    for s_idx, polarity in polarity_idxs:
        sentiment_text_no=tokens[s_idx]['text_no']
        s_idx_pertext=tokens[s_idx]['index_pertext']
        
        #n単語が属するtext_noごとにdict型再構成
        sentiment_text_key=['index','index_pertext','surface','pos','sub_pos','lemma','inflection']
        sentiment_text=[]
        for token in tokens:
            if token['text_no']==sentiment_text_no:
                sentiment_text_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']] # index_per_sentence,sentimentは一旦全て0
                sentiment_text.append(dict(zip(sentiment_text_key,sentiment_text_values)))

# sentimentが名詞の場合(規則4)-----------
        if sentiment_text[s_idx_pertext]['pos']=='名詞':
            #print("名詞だよ")
            subject_by_sentiment_chk=[] #主語があるか確認用
            subject_lemmas_by_sentiment_chk=[]
            predicate_by_sentiment_chk=[] #述語があるか確認用
            predicate_lemmas_by_sentiment_chk=[]

            # n単語より後ろに述語があるか判定
            ## 一旦n単語(名詞)を述語とした上で検索(間に名詞があれば検索ストップさせるため)
            predicate_by_sentiment_chk.append(sentiment_text[s_idx_pertext]['index'])
            extract_reason_predicates(0,
                     sentiment_text,
                     s_idx_pertext+1,
                     predicate_by_sentiment_chk, 
                     predicate_lemmas_by_sentiment_chk,
                     predicate_lemmas_by_sentiment_chk,
                     )
            
            # n単語より前に名詞があるか判定
            extract_reason_subjects(0, # 前方検索
                     sentiment_text,
                     s_idx_pertext-1, #n単語(名詞)は検索対象に含まない
                     subject_by_sentiment_chk,
                     subject_lemmas_by_sentiment_chk,
                     )

            #sentiment以降に述語がある場合
            if len(predicate_by_sentiment_chk)>1:
                #print("sentiment以降に述語がある場合")
                # (n単語+以前の名詞)を主語にする
                extract_reason_subjects(0, # n単語より前方の名詞検索
                         sentiment_text,
                         s_idx_pertext, #n単語(名詞)は検索対象に含める
                         subject_by_sentiment,
                         subject_lemmas_by_sentiment,
                         )
                #print('subject_lemmas_by_sentiment  ',subject_lemmas_by_sentiment)
                
                # 述語検索済み,chkからコピー
                predicate_by_sentiment=predicate_by_sentiment_chk[1:] # 述語にしたn単語は除去
                predicate_lemmas_by_sentiment=predicate_lemmas_by_sentiment_chk
                
                #print('predicate_lemmas_by_sentiment:',predicate_lemmas_by_sentiment)
            #sentiment以降に述語がない場合    
            elif len(predicate_by_sentiment_chk)==1:
                #print("sentiment以降に述語がない場合")
                if len(subject_by_sentiment_chk)>0: #直前に名詞がある場合
                    #print("直前に名詞がある場合")

                    # 主語検索済み,chkからコピー
                    subject_by_sentiment=subject_by_sentiment_chk
                    subject_lemmas_by_sentiment=subject_lemmas_by_sentiment_chk
                
                    # n単語(名詞)を述語に
                    predicate_by_sentiment.append(sentiment_text[s_idx_pertext]['index'])
                    predicate_lemmas_by_sentiment.append(sentiment_text[s_idx_pertext]['lemma']) 
                    # n単語から前方にも述語があれば保存
                    extract_reason_predicates(1,
                             sentiment_text,
                             s_idx_pertext-1,
                             predicate_by_sentiment, 
                             predicate_lemmas_by_sentiment,
                             predicate_lemmas_by_sent_tmp,
                             )
                    
                elif len(subject_by_sentiment_chk)==0: #直前に名詞が無い場合
                    #print("直前に名詞がない場合")
                    # n単語(名詞)を主語に
                    subject_by_sentiment.append(sentiment_text[s_idx_pertext]['index'])
                    subject_lemmas_by_sentiment.append(sentiment_text[s_idx_pertext]['lemma'])   
                    
                    # 述語はNone
                    predicate_by_sentiment.append('None')

# sentimentが述語の場合--------------            
        elif sentiment_text[s_idx_pertext]['pos'] in ['動詞','形容詞','形容動詞']:

            # N形容詞+名詞の場合 (規則3 主語:名詞, 述語:N形容詞とする)
            
            if (sentiment_text[s_idx_pertext]['pos']=='形容詞' and                # 形容詞で
                
                ((len(sentiment_text)-1>s_idx_pertext and                        # 次の単語が名詞
                sentiment_text[s_idx_pertext+1]['pos']=='名詞' and
                sentiment_text[s_idx_pertext+1]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']) or
                 
                (len(sentiment_text)-2>s_idx_pertext and                        # or 次の次まで単語があり
                sentiment_text[s_idx_pertext+1]['pos'] in ['助動詞'] and ## 次が助詞/助動詞で
                sentiment_text[s_idx_pertext+2]['pos']=='名詞' and
                sentiment_text[s_idx_pertext+2]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']))):### 次の次が名詞
                
                # 助詞も追加予定(全助詞ではなく特定)
                ## ～凄くて物販... は例外としたい
                
                #print("N形容詞+名詞の場合")
                #print(sentiment_text[s_idx_pertext]['lemma'])
                # 述語検索
                extract_reason_predicates(0, #後方検索
                         sentiment_text,
                         s_idx_pertext+1, # 直後の名詞から検索
                         predicate_by_sentiment,
                         predicate_lemmas_by_sentiment,
                         predicate_lemmas_by_sent_tmp,
                         )
                predicate_by_sentiment.append(sentiment_text[s_idx_pertext]['index']) # 末尾にN形容詞追加
                predicate_lemmas_by_sentiment.append(sentiment_text[s_idx_pertext]['lemma'])
                
                # 主語検索
                #print("chk:",predicate_by_sentiment[0])
                #print("chk:",predicate_lemmas_by_sentiment[0])
                if len(predicate_by_sentiment)>1: # N形容詞+名詞以降に述語が続く場合
                    extract_reason_subjects(0, # 前方検索
                             sentiment_text,
                             tokens[predicate_by_sentiment[0]]['index_pertext'], # 先頭の述語から検索(注:文章を通してのindex)
                             subject_by_sentiment,
                             subject_lemmas_by_sentiment,
                             )
                elif len(predicate_by_sentiment)==1: # N形容詞しか述語がない場合
                    extract_reason_subjects(0, # 前方検索
                             sentiment_text,
                             len(sentiment_text)-1, # 文末尾から検索
                             subject_by_sentiment,
                             subject_lemmas_by_sentiment,
                             )  
                # 主語が見つからない場合None (例:辛い+日々(不可名詞))
                if len(subject_by_sentiment)==0:
                    subject_by_sentiment.append('None')
            # 形容動詞+な/(みたい)な/の+名詞の場合(規則3) 
            ## "みたいな"は"みたい"をstop_word定義して対応     
                
            elif ((sentiment_text[s_idx_pertext]['pos']=='形容動詞' and # 形容動詞で
                len(sentiment_text)-2>s_idx_pertext and
                sentiment_text[s_idx_pertext+2]['pos']=='名詞' and # 次の次が名詞 ex "最悪の","絶望の"
                sentiment_text[s_idx_pertext+2]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']) and
                  
                ((sentiment_text[s_idx_pertext+1]['pos']=='助動詞' and 
                sentiment_text[s_idx_pertext+1]['surface']=='な' and
                sentiment_text[s_idx_pertext+1]['inflection']=='体言接続') or # 間に助動詞'な'が続く 
                                                                  
                (sentiment_text[s_idx_pertext+1]['pos']=='助詞' and    
                sentiment_text[s_idx_pertext+1]['surface'] in ['の']))): # or間に助詞'の'が続く  
                

            
                #print("N形容動詞+名詞の場合")
                #print(sentiment_text[s_idx_pertext]['lemma'])
                # 述語検索 (N形容詞+名詞の場合と同じ処理)----
                extract_reason_predicates(0, #後方検索
                         sentiment_text,
                         s_idx_pertext+1, # 直後の名詞から検索
                         predicate_by_sentiment,
                         predicate_lemmas_by_sentiment,
                         predicate_lemmas_by_sent_tmp,
                         )
                predicate_by_sentiment.append(sentiment_text[s_idx_pertext]['index']) # 末尾にN形容詞追加
                predicate_lemmas_by_sentiment.append(sentiment_text[s_idx_pertext]['lemma'])
                #print('predicate_by_sentiment!!:',predicate_lemmas_by_sentiment)
                #print("ind:::",predicate_by_sentiment[0])
                # 主語検索
                if len(predicate_by_sentiment)>1: # N形容詞+名詞以降に述語が続く場合
                    extract_reason_subjects(0, # 前方検索
                             sentiment_text,
                             tokens[predicate_by_sentiment[0]]['index_pertext'], # 先頭の述語から検索(注:文章を通してのindex)
                             subject_by_sentiment,
                             subject_lemmas_by_sentiment,
                             )
                elif len(predicate_by_sentiment)==1: # N形容詞しか述語がない場合
                    extract_reason_subjects(0, # 前方検索
                             sentiment_text,
                             len(sentiment_text)-1, # 文末尾から検索
                             subject_by_sentiment,
                             subject_lemmas_by_sentiment,
                             )  
                # 主語が見つからない場合None
                if len(subject_by_sentiment)==0:
                    subject_by_sentiment.append('None')
                # ----------------------------------------
                
            else:    

                for k in range(text_num): # 1文ずつsentimentの検索
                #while(True):
                    
                    #主語S検索
                    ## 文の結合なしor文前方に結合する場合,n単語から逆順に名詞検索
                    ### 文後方に結合する場合,文末から逆順に名詞検索
                    extract_reason_subjects(conn_reverse,
                             sentiment_text,
                             s_idx_pertext,
                             subject_by_sentiment,
                             subject_lemmas_by_sentiment,
                             )
                    #述語V検索
                    if conn_reverse==0:
                        # n単語から前方に述語検索
                        extract_reason_predicates(1,
                                 sentiment_text,
                                 s_idx_pertext,
                                 predicate_by_sentiment,
                                 predicate_lemmas_by_sentiment,
                                 predicate_lemmas_by_sent_tmp,
                                 )
                        # n単語から文末まで述語検索
                        extract_reason_predicates(0,
                                 sentiment_text,
                                 s_idx_pertext,
                                 predicate_by_sentiment,
                                 predicate_lemmas_by_sentiment,
                                 predicate_lemmas_by_sent_tmp,
                                 )
    
                    elif conn_reverse==1: # 後文につなげる場合
                        # 文末から前方に述語検索
                        extract_reason_predicates(1,
                                 sentiment_text,
                                 len(sentiment_text)-1, # 検索開始位置は文末
                                 predicate_by_sentiment,
                                 predicate_lemmas_by_sentiment,
                                 predicate_lemmas_by_sent_tmp,
                                 )
                        
                    # 主語が検索できなかった場合
                    if len(subject_by_sentiment)==0:
                    
                        # 文がN単語述語で始まる場合,同文内末尾に名詞があれば主語とする(N文頭規則)
                        if k == 0: # 最初の文の検索時のみ実施(2回目以降は文の結合をする)
                            extract_reason_subjects(1,
                                     sentiment_text,
                                     s_idx_pertext,
                                     subject_by_sentiment,
                                     subject_lemmas_by_sentiment,
                                     )       
                            if len(subject_by_sentiment) > 0: # 同文内後半に主語がある場合
                                             ## 文末から前方の述語も検索する
                                extract_reason_predicates(1,
                                         sentiment_text,
                                         len(sentiment_text)-1, # 検索開始位置は文末
                                         predicate_by_sentiment,
                                         predicate_lemmas_by_sentiment,
                                         predicate_lemmas_by_sent_tmp,
                                         )

                                
                                break
                            
                        #1文しかない場合
                        if max_text_no==1: 
                            #print('単文で主語見つかりません')
                            subject_by_sentiment.append('None')
                            break           
                        # 前文がある場合,前文につなげる
                        elif sentiment_text_no>1 and conn_reverse==0:
                            
                            for token in tokens:
                                if token['text_no']>=sentiment_text_no:# 同文以降の文No.を一つ下げる
                                    token['text_no']=token['text_no']-1 
                            sentiment_text_no=sentiment_text_no-1# N文No.も一つ下げる
                            
                            # text_no振り直し後のindex振り直しと,最大text_no,n単語が属する文再取得
                            i=0
                            max_text_no=1
                            sentiment_text.clear()
                            for token in tokens:
                                if token['text_no']==sentiment_text_no: 
                                    token['index_pertext']=i #ネガ文のindex振り直し
                                    i=i+1
                                    sentiment_text_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']]
                                    sentiment_text.append(dict(zip(sentiment_text_key,sentiment_text_values)))
                                if token['index']==s_idx: # n単語のindex更新
                                    s_idx_pertext=token['index_pertext']
                                if token['text_no']>max_text_no: # 最大text_no
                                    max_text_no=token['text_no']
                                    
                            ##print('text_no変更[前文につなげる]:',tokens)                        
    
                            #print('predicate_lemmas_by_sentiment:',predicate_lemmas_by_sentiment)
                            predicate_by_sent_tmp[len(predicate_by_sent_tmp):len(predicate_by_sent_tmp)]=predicate_by_sentiment
                            predicate_lemmas_by_sent_tmp[len(predicate_lemmas_by_sent_tmp):len(predicate_lemmas_by_sent_tmp)]=predicate_lemmas_by_sentiment #文結合後の単語の順番保持のため,述語は他の場所に退避
                            predicate_by_sentiment.clear()
                            predicate_lemmas_by_sentiment.clear()
                            #print('predicate_lemmas_by_sent_tmp:',predicate_lemmas_by_sent_tmp)
                            
                            continue# 再度S,V検索へ
                            
                        # 全文探しても主語が無い場合
                        elif sentiment_text_no==max_text_no and conn_reverse==1:
                            #print('全文で主語見つかりません')
                            subject_by_sentiment.append('None')
                            break
                        
                        # 前文がない場合,後文につなげる
                        elif sentiment_text_no==1 or conn_reverse==1:
                            
                            for token in tokens:
                                if token['text_no']>sentiment_text_no: # 後文以降の文No.を一つ下げる
                                    token['text_no']=token['text_no']-1 
    
                            # text_no振り直し後のindex振り直しと,最大text_no,n単語が属する文再取得
                            i=0
                            max_text_no=1
                            sentiment_text.clear()
                            for token in tokens:
                                if token['text_no']==sentiment_text_no: 
                                    token['index_pertext']=i #ネガ文のindex振り直し
                                    i=i+1
                                    sentiment_text_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']]
                                    sentiment_text.append(dict(zip(sentiment_text_key,sentiment_text_values)))
                                if token['index']==s_idx:
                                    s_idx_pertext=token['index_pertext']
                                if token['text_no']>max_text_no:
                                    max_text_no=token['text_no']
                                        
                            ##print('text_no変更[後文につなげる]:',tokens)
                                       
                                    
                            #print('predicate_lemmas_by_sentiment:',predicate_lemmas_by_sentiment)
                            predicate_by_sent_tmp[len(predicate_by_sent_tmp):len(predicate_by_sent_tmp)]=predicate_by_sentiment
                            predicate_lemmas_by_sent_tmp[len(predicate_lemmas_by_sent_tmp):len(predicate_lemmas_by_sent_tmp)]=predicate_lemmas_by_sentiment #文結合後の単語の順番保持のため,述語は他の場所に退避
                            predicate_by_sentiment.clear()
                            predicate_lemmas_by_sentiment.clear()
                            #print('predicate_lemmas_by_sent_tmp:',predicate_lemmas_by_sent_tmp)
                            
                            conn_reverse=1 #文後方結合フラグ立てる
                            
                            continue# 再度S,V検索へ
                            
                        
                    else: #主語があれば検索終了
                        break
                    
                    if k + 1 == text_num: # 全文探しても主語がない場合(現状for文内で必ず主語が見つかるかNoneになるが、想定外のエラー時のため。)
                        subject_by_sentiment.append('None')
            
                
        else: #n単語の品詞が名詞,動詞,形容詞,形容動詞以外
            subject_by_sentiment.append('None')
            predicate_by_sentiment.append('None')

 #文結合した場合,退避した述語を結合                   
        if len(predicate_by_sent_tmp)!=0: 
            predicate_by_sentiment[len(predicate_by_sentiment):len(predicate_by_sentiment)]=predicate_by_sent_tmp
            predicate_lemmas_by_sentiment[len(predicate_lemmas_by_sentiment):len(predicate_lemmas_by_sentiment)]=predicate_lemmas_by_sent_tmp
            
        subjects_by_sentiment.append(copy.copy(subject_by_sentiment))
        predicates_by_sentiment.append(copy.copy(predicate_by_sentiment))

## 2.以降未実装

        # n単語ごとの検索が終わるごとにn_subject,n_predicateはリセット、次のN単語へ
        subject_by_sentiment.clear()
        predicate_by_sentiment.clear()
        subject_lemmas_by_sentiment.clear()
        predicate_lemmas_by_sentiment.clear()
        predicate_by_sent_tmp.clear()
        predicate_lemmas_by_sent_tmp.clear()
        conn_reverse=0
        polarity_by_sentiment.append(polarity)

    sentiment_reasons=[] # subjects_by_sentiment,predicates_by_sentimentを辞書型に変換して返却
    keys = ['subject','predicates','sentiment_type']
    for subject_by_sentiment,predicate_by_sentiment,polarity in zip(subjects_by_sentiment,predicates_by_sentiment,polarity_by_sentiment):
        values = [subject_by_sentiment,predicate_by_sentiment,polarity]
        sentiment_reasons.append(dict(zip(keys, values)))
        
    return sentiment_reasons



def extract_reason_records(processed_reviews: list[dict]) -> list[dict]:

    all_reasons = []

    for review in processed_reviews:
        reasons = extract_reason_pairs(review['tokens'])
        all_reasons.append(reasons)

    return all_reasons

