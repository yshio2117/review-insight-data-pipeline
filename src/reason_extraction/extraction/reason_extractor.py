import csv
import copy
from pathlib import Path


def extract_reason_subjects(search_from_end,
             sentiment_sentence,
             start_index,
             ext_subjects_in_sentence,
             ext_subject_lemmas,
             ):
    """
    Search negative/positive subjects (in the same sentence as sentiment term).)

    Parameters
    ----------
    search_from_end : bool
        false: search for subjects from polarity term to the beginning of the sentence, true: search for subjects from the end of sentence.)
    sentiment_sentence : list of tokens
        sentence that polarity term belongs. e.g. [{'sentiment':0,'index':0,'index_pertext':0,'lemma':'ホテル',},{...},..]
    start_index : int
        index to search from (in sentiment_sentence).
    ext_subjects_in_sentence : list
        indice of extracted subjects.        
    ext_subject_lemmas : list
        lemmas of extracted subjects.

    Returns
    -------
    None (update ext_subjects_in_sentence, ext_subject_lemmas in place)

    """


    # 検索範囲指定 n単語から前方に検索 or 文末から前方に検索
    ## N単語自身も検索対象に含む
    search_range = start_index+1 if not search_from_end else len(sentiment_sentence)
    
    sp_particle = 0 # 特定助詞フラグ（1の間は動詞/形容詞/形容動詞を検索終了条件としない）
    # 該当する名詞がある限り検索
    for index_pertext in reversed(range(0,search_range)):

        # 名詞が繰り返す限り取得.主語不可名詞は除く('非自立'等)
        if sentiment_sentence[index_pertext]['pos']=='名詞' and sentiment_sentence[index_pertext]['sub_pos'] not in ['非自立','副詞可能','接尾','代名詞','特殊','数']:
            if sentiment_sentence[index_pertext]['lemma'] not in ['ー','人','人達','者','子','方','やつ','奴','こと','事']: # 長音記号(名詞,一般),mecab上接尾とならない名詞も主語不可(解析結果を接尾に修正してもよい. 
                ext_subjects_in_sentence.append((sentiment_sentence[index_pertext]['index'])) #元のindex番号を主語として保存
                ext_subject_lemmas.append(sentiment_sentence[index_pertext]['lemma'])
                sp_particle=0
                            
        # 読点等はスキップして次へ
        #elif sentiment_sentence[index_pertext]['pos']=='記号' and sentiment_sentence[index_pertext]['sub_pos'] in ['読点','括弧閉','括弧開','一般']: # 読点等はスキップ
        #    continue
        
    # 主語前　名詞+動詞/形容詞/形容動詞+特定助詞は主語として取得(規則7)
        elif len(ext_subjects_in_sentence)>0 and ((sentiment_sentence[index_pertext]['pos']=='助詞' and sentiment_sentence[index_pertext]['lemma'] in 
                                                                            ['けど','のに','から','て','ば'])\
                             # 規則8 仮定形助動詞も同様の扱い
                          or (sentiment_sentence[index_pertext]['pos']=='助動詞' and sentiment_sentence[index_pertext]['inflection'] == '仮定形')):
            sp_particle=1
            continue
        # 特定助詞条件で非主語名詞が来た場合検索条件終了
        elif sp_particle == 1 and sentiment_sentence[index_pertext]['pos'] in ['名詞']\
                              and sentiment_sentence[index_pertext]['lemma'] not in ['ん']: # 非自立名詞'ん'は例外でスキップ
            sp_particle=0


        # 動詞,形容詞,形容動詞,が続いたら検索ストップ(すでにn_subjectが取得された場合のみ)        
        elif sp_particle == 0 and len(ext_subjects_in_sentence)>0 and sentiment_sentence[index_pertext]['pos'] in ['動詞','形容詞','形容動詞']:
            break 

        
    ext_subjects_in_sentence.reverse()# 逆から取得しているので逆順に
    ext_subject_lemmas.reverse()    
    

    
def extract_reason_predicates(search_backward,
             sentiment_sentence,
             start_index,
             ext_predicates_in_sentence,
             ext_predicate_lemmas,
             ext_predicate_lemmas_tmp
             ):
    """
    Search negative/positive predicates (in the same sentence as sentiment term).
 
    Parameters
    ----------
    search_backward : bool
        False:search from polarity term to the end of sentence, True:search from polarity term to the beginning of sentence.
    sentiment_sentence : list
        sentence that polarity term belongs. e.g. [{'sentiment':0,'index':0,'index_pertext':0,'lemma':'ホテル',},{...},..]
    start_index : int
        index to search from (in sentiment_sentence).
    ext_predicates_in_sentence : list
        indice of extracted predicates        
    ext_predicate_lemmas : list
        lemmas of extracted predicates
    ext_predicate_lemmas_tmp : list
        temporary storage for lemmas of extracted predicates for order preservation when sentence combination occurs.
        
    Returns
    -------
    None (update ext_predicates_in_sentence,ext_predicate_lemmas in place)

    """
    
                
    num_before=len(ext_predicates_in_sentence) # 該当述語があるか判定用
    
    # 検索範囲指定            
    if search_backward:# n単語から前方に述語検索
        search_range=reversed(range(0,start_index+1))
    else:# n単語から文末まで述語検索
        search_range = range(start_index,len(sentiment_sentence)) 
        
    
    # 述語が繰り返す限り取得
    for index_pertext in search_range:
        # 述語になり得る動詞,形容詞,形容動詞であれば保存(述語に関しては重複はすべて除く)
        if  sentiment_sentence[index_pertext]['pos'] in ['動詞','形容詞','形容動詞'] and (sentiment_sentence[index_pertext]['lemma'] not in ext_predicate_lemmas
                                                          and sentiment_sentence[index_pertext]['lemma'] not in ext_predicate_lemmas_tmp): # 重複は除外（述語のみ)
            #if sentiment_sentence[index_pertext]['sub_pos']=="非自立" and sentiment_sentence[index_pertext]['lemma'] in ["過ぎる","すぎる"]:
            #if sentiment_sentence[index_pertext]['sub_pos'] not in ["自立","形容動詞語幹","サ変接続"]:
            if sentiment_sentence[index_pertext]['sub_pos'] in ["非自立","接尾"] or sentiment_sentence[index_pertext]['lemma'] in ["過ぎる","すぎる"]:    
                continue # V+過ぎるは一旦全除外
                
                
            ext_predicates_in_sentence.append(sentiment_sentence[index_pertext]['index'])# 文章におけるindexを保存(文におけるindexではない)
            ext_predicate_lemmas.append(sentiment_sentence[index_pertext]['lemma'])# 原形も保存
            
        # 主語になりえる単語(自立名詞等)があればそこで検索ストップ
        elif ((len(ext_predicates_in_sentence)>0 or len(ext_predicate_lemmas_tmp)>0) and 
              sentiment_sentence[index_pertext]['pos'] in ['名詞'] and 
              sentiment_sentence[index_pertext]['sub_pos'] not in ['非自立','副詞可能','接尾','代名詞','特殊','数'] and
              sentiment_sentence[index_pertext]['lemma'] not in ['ー','人','人達','者','子','方','やつ','奴','こと','事']):
            break
        
    if num_before<len(ext_predicates_in_sentence) and search_backward:# 逆から取得しているので逆順に並び変え（該当述語があった場合)       
        ext_predicates_in_sentence.reverse()
        ext_predicate_lemmas.reverse()
    


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
    
    
    
    ext_subjects_in_text=[]# 投稿内の全n_subject
    ext_predicates_in_text=[]# 投稿内の全n_predicate
    ext_subjects_in_sentence=[]# n単語ごとのn_subject
    ext_predicates_in_sentence=[]# n単語ごとのn_predicate
    polarity_by_sentiment=[] # 検索する極性単語の極性(positive/negative)
    ext_predicate_lemmas=[]# n_predicate重複チェック用に原形を入れる(現状は原形で重複チェック)
    ext_subject_lemmas=[]
    #n_sentences=[]# (未使用) 規則6 n_subject,n_predicateの重複除外用[(n_subject1,n_predicate1),(n_subject2,n_predicate2),...)
    ext_predicates_tmp=[]# 文結合後の単語の順番保持用に一時保存させる.並び変え後ext_predicates_in_sentenceに移動する
    ext_predicate_lemmas_tmp=[]
    search_from_end=False #文後方結合フラグ(前方に結合する場合False,後方に結合する場合True)
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
        sentiment_sentence_no=tokens[s_idx]['text_no']
        s_idx_pertext=tokens[s_idx]['index_pertext']
        
        #n単語が属するtext_noごとにdict型再構成
        sentiment_sentence_key=['index','index_pertext','surface','pos','sub_pos','lemma','inflection']
        sentiment_sentence=[]
        for token in tokens:
            if token['text_no']==sentiment_sentence_no:
                sentiment_sentence_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']] # index_per_sentence,sentimentは一旦全て0
                sentiment_sentence.append(dict(zip(sentiment_sentence_key,sentiment_sentence_values)))

# sentimentが名詞の場合(規則4)-----------
        if sentiment_sentence[s_idx_pertext]['pos']=='名詞':
            #print("名詞だよ")
            test_to_extract_subject=[] #主語があるか確認用
            test_to_ext_subject_lemmas=[]
            test_to_extract_predicate=[] #述語があるか確認用
            test_to_ext_predicate_lemmas=[]

            # n単語より後ろに述語があるか判定
            ## 一旦n単語(名詞)を述語とした上で検索(間に名詞があれば検索ストップさせるため)
            test_to_extract_predicate.append(sentiment_sentence[s_idx_pertext]['index'])
            extract_reason_predicates(search_backward=False,
                     sentiment_sentence=sentiment_sentence,
                     start_index=s_idx_pertext+1,
                     ext_predicates_in_sentence=test_to_extract_predicate, 
                     ext_predicate_lemmas=test_to_ext_predicate_lemmas,
                     ext_predicate_lemmas_tmp=test_to_ext_predicate_lemmas,
                     )
            
            # n単語より前に名詞があるか判定
            extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                     sentiment_sentence=sentiment_sentence,
                     start_index=s_idx_pertext-1, #n単語(名詞)は検索対象に含まない
                     ext_subjects_in_sentence=test_to_extract_subject,
                     ext_subject_lemmas=test_to_ext_subject_lemmas,
                     )

            #sentiment以降に述語がある場合
            if len(test_to_extract_predicate)>1:
                #print("sentiment以降に述語がある場合")
                # (n単語+以前の名詞)を主語にする
                extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                         sentiment_sentence=sentiment_sentence,
                         start_index=s_idx_pertext, #n単語(名詞)は検索対象に含める
                         ext_subjects_in_sentence=ext_subjects_in_sentence,
                         ext_subject_lemmas=ext_subject_lemmas,
                         )
                #print('ext_subject_lemmas  ',ext_subject_lemmas)
                
                # 述語検索済み,chkからコピー
                ext_predicates_in_sentence=test_to_extract_predicate[1:] # 述語にしたn単語は除去
                ext_predicate_lemmas=test_to_ext_predicate_lemmas
                
                #print('ext_predicate_lemmas:',ext_predicate_lemmas)
            #sentiment以降に述語がない場合    
            elif len(test_to_extract_predicate)==1:
                #print("sentiment以降に述語がない場合")
                if len(test_to_extract_subject)>0: #直前に名詞がある場合
                    #print("直前に名詞がある場合")

                    # 主語検索済み,chkからコピー
                    ext_subjects_in_sentence=test_to_extract_subject
                    ext_subject_lemmas=test_to_ext_subject_lemmas
                
                    # n単語(名詞)を述語に
                    ext_predicates_in_sentence.append(sentiment_sentence[s_idx_pertext]['index'])
                    ext_predicate_lemmas.append(sentiment_sentence[s_idx_pertext]['lemma']) 
                    # n単語から前方にも述語があれば保存
                    extract_reason_predicates(search_backward=True,
                             sentiment_sentence=sentiment_sentence,
                             start_index=s_idx_pertext-1,
                             ext_predicates_in_sentence=ext_predicates_in_sentence, 
                             ext_predicate_lemmas=ext_predicate_lemmas,
                             ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                             )
                    
                elif len(test_to_extract_subject)==0: #直前に名詞が無い場合
                    #print("直前に名詞がない場合")
                    # n単語(名詞)を主語に
                    ext_subjects_in_sentence.append(sentiment_sentence[s_idx_pertext]['index'])
                    ext_subject_lemmas.append(sentiment_sentence[s_idx_pertext]['lemma'])   
                    
                    # 述語はNone
                    ext_predicates_in_sentence.append('None')

# sentimentが述語の場合--------------            
        elif sentiment_sentence[s_idx_pertext]['pos'] in ['動詞','形容詞','形容動詞']:

            # N形容詞+名詞の場合 (規則3 主語:名詞, 述語:N形容詞とする)
            
            if (sentiment_sentence[s_idx_pertext]['pos']=='形容詞' and                # 形容詞で
                
                ((len(sentiment_sentence)-1>s_idx_pertext and                        # 次の単語が名詞
                sentiment_sentence[s_idx_pertext+1]['pos']=='名詞' and
                sentiment_sentence[s_idx_pertext+1]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']) or
                 
                (len(sentiment_sentence)-2>s_idx_pertext and                        # or 次の次まで単語があり
                sentiment_sentence[s_idx_pertext+1]['pos'] in ['助動詞'] and ## 次が助詞/助動詞で
                sentiment_sentence[s_idx_pertext+2]['pos']=='名詞' and
                sentiment_sentence[s_idx_pertext+2]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']))):### 次の次が名詞
                
                # 助詞も追加予定(全助詞ではなく特定)
                ## ～凄くて物販... は例外としたい
                
                #print("N形容詞+名詞の場合")
                #print(sentiment_sentence[s_idx_pertext]['lemma'])
                # 述語検索
                extract_reason_predicates(search_backward=False, #後方検索
                         sentiment_sentence=sentiment_sentence,
                         start_index=s_idx_pertext+1, # 直後の名詞から検索
                         ext_predicates_in_sentence=ext_predicates_in_sentence,
                         ext_predicate_lemmas=ext_predicate_lemmas,
                         ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                         )
                ext_predicates_in_sentence.append(sentiment_sentence[s_idx_pertext]['index']) # 末尾にN形容詞追加
                ext_predicate_lemmas.append(sentiment_sentence[s_idx_pertext]['lemma'])
                
                # 主語検索
                #print("chk:",ext_predicates_in_sentence[0])
                #print("chk:",ext_predicate_lemmas[0])
                if len(ext_predicates_in_sentence)>1: # N形容詞+名詞以降に述語が続く場合
                    extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                             sentiment_sentence=sentiment_sentence,
                             start_index=tokens[ext_predicates_in_sentence[0]]['index_pertext'], # 先頭の述語から検索(注:文章を通してのindex)
                             ext_subjects_in_sentence=ext_subjects_in_sentence,
                             ext_subject_lemmas=ext_subject_lemmas,
                             )
                elif len(ext_predicates_in_sentence)==1: # N形容詞しか述語がない場合
                    extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                             sentiment_sentence=sentiment_sentence,
                             start_index=len(sentiment_sentence)-1, # 文末尾から検索
                             ext_subjects_in_sentence=ext_subjects_in_sentence,
                             ext_subject_lemmas=ext_subject_lemmas,
                             )  
                # 主語が見つからない場合None (例:辛い+日々(不可名詞))
                if len(ext_subjects_in_sentence)==0:
                    ext_subjects_in_sentence.append('None')
            # 形容動詞+な/(みたい)な/の+名詞の場合(規則3) 
            ## "みたいな"は"みたい"をstop_word定義して対応     
                
            elif ((sentiment_sentence[s_idx_pertext]['pos']=='形容動詞' and # 形容動詞で
                len(sentiment_sentence)-2>s_idx_pertext and
                sentiment_sentence[s_idx_pertext+2]['pos']=='名詞' and # 次の次が名詞 ex "最悪の","絶望の"
                sentiment_sentence[s_idx_pertext+2]['sub_pos'] not in ['非自立','接尾','代名詞','特殊']) and
                  
                ((sentiment_sentence[s_idx_pertext+1]['pos']=='助動詞' and 
                sentiment_sentence[s_idx_pertext+1]['surface']=='な' and
                sentiment_sentence[s_idx_pertext+1]['inflection']=='体言接続') or # 間に助動詞'な'が続く 
                                                                  
                (sentiment_sentence[s_idx_pertext+1]['pos']=='助詞' and    
                sentiment_sentence[s_idx_pertext+1]['surface'] in ['の']))): # or間に助詞'の'が続く  
                

            
                #print("N形容動詞+名詞の場合")
                #print(sentiment_sentence[s_idx_pertext]['lemma'])
                # 述語検索 (N形容詞+名詞の場合と同じ処理)----
                extract_reason_predicates(search_backward=False, #後方検索
                         sentiment_sentence=sentiment_sentence,
                         start_index=s_idx_pertext+1, # 直後の名詞から検索
                         ext_predicates_in_sentence=ext_predicates_in_sentence,
                         ext_predicate_lemmas=ext_predicate_lemmas,
                         ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                         )
                ext_predicates_in_sentence.append(sentiment_sentence[s_idx_pertext]['index']) # 末尾にN形容詞追加
                ext_predicate_lemmas.append(sentiment_sentence[s_idx_pertext]['lemma'])
                #print('ext_predicates_in_sentence!!:',ext_predicate_lemmas)
                #print("ind:::",ext_predicates_in_sentence[0])
                # 主語検索
                if len(ext_predicates_in_sentence)>1: # N形容詞+名詞以降に述語が続く場合
                    extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                             sentiment_sentence=sentiment_sentence,
                             start_index=tokens[ext_predicates_in_sentence[0]]['index_pertext'], # 先頭の述語から検索(注:文章を通してのindex)
                             ext_subjects_in_sentence=ext_subjects_in_sentence,
                             ext_subject_lemmas=ext_subject_lemmas,
                             )
                elif len(ext_predicates_in_sentence)==1: # N形容詞しか述語がない場合
                    extract_reason_subjects(search_from_end=False, # search from sentiment term to the beginning of the sentence
                             sentiment_sentence=sentiment_sentence,
                             start_index=len(sentiment_sentence)-1, # 文末尾から検索
                             ext_subjects_in_sentence=ext_subjects_in_sentence,
                             ext_subject_lemmas=ext_subject_lemmas,
                             )  
                # 主語が見つからない場合None
                if len(ext_subjects_in_sentence)==0:
                    ext_subjects_in_sentence.append('None')
                # ----------------------------------------
                
            else:    

                for k in range(text_num): # 1文ずつsentimentの検索
                #while(True):
                    
                    #主語S検索
                    ## 文の結合なしor文前方に結合する場合,n単語から逆順に名詞検索
                    ### 文後方に結合する場合,文末から逆順に名詞検索
                    extract_reason_subjects(search_from_end,
                             sentiment_sentence=sentiment_sentence,
                             start_index=s_idx_pertext,
                             ext_subjects_in_sentence=ext_subjects_in_sentence,
                             ext_subject_lemmas=ext_subject_lemmas,
                             )
                    #述語V検索
                    if search_from_end==False:
                        # n単語から前方に述語検索
                        extract_reason_predicates(search_backward=True,
                                 sentiment_sentence=sentiment_sentence,
                                 start_index=s_idx_pertext,
                                 ext_predicates_in_sentence=ext_predicates_in_sentence,
                                 ext_predicate_lemmas=ext_predicate_lemmas,
                                 ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                                 )
                        # n単語から文末まで述語検索
                        extract_reason_predicates(search_backward=False,
                                 sentiment_sentence=sentiment_sentence,
                                 start_index=s_idx_pertext,
                                 ext_predicates_in_sentence=ext_predicates_in_sentence,
                                 ext_predicate_lemmas=ext_predicate_lemmas,
                                 ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                                 )
    
                    elif search_from_end: # 後文につなげる場合
                        # 文末から前方に述語検索
                        extract_reason_predicates(search_backward=True,
                                 sentiment_sentence=sentiment_sentence,
                                 start_index=len(sentiment_sentence)-1, # 検索開始位置は文末
                                 ext_predicates_in_sentence=ext_predicates_in_sentence,
                                 ext_predicate_lemmas=ext_predicate_lemmas,
                                 ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                                 )
                        
                    # 主語が検索できなかった場合
                    if len(ext_subjects_in_sentence)==0:
                    
                        # 文がN単語述語で始まる場合,同文内末尾に名詞があれば主語とする(N文頭規則)
                        if k == 0: # 最初の文の検索時のみ実施(2回目以降は文の結合をする)
                            extract_reason_subjects(search_from_end=True,
                                     sentiment_sentence=sentiment_sentence,
                                     start_index=s_idx_pertext,
                                     ext_subjects_in_sentence=ext_subjects_in_sentence,
                                     ext_subject_lemmas=ext_subject_lemmas,
                                     )       
                            if len(ext_subjects_in_sentence) > 0: # 同文内後半に主語がある場合
                                             ## 文末から前方の述語も検索する
                                extract_reason_predicates(search_backward=True,
                                         sentiment_sentence=sentiment_sentence,
                                         start_index=len(sentiment_sentence)-1, # 検索開始位置は文末
                                         ext_predicates_in_sentence=ext_predicates_in_sentence,
                                         ext_predicate_lemmas=ext_predicate_lemmas,
                                         ext_predicate_lemmas_tmp=ext_predicate_lemmas_tmp,
                                         )

                                
                                break
                            
                        #1文しかない場合
                        if max_text_no==1: 
                            #print('単文で主語見つかりません')
                            ext_subjects_in_sentence.append('None')
                            break           
                        # 前文がある場合,前文につなげる
                        elif sentiment_sentence_no>1 and not search_from_end:
                            
                            for token in tokens:
                                if token['text_no']>=sentiment_sentence_no:# 同文以降の文No.を一つ下げる
                                    token['text_no']=token['text_no']-1 
                            sentiment_sentence_no=sentiment_sentence_no-1# N文No.も一つ下げる
                            
                            # text_no振り直し後のindex振り直しと,最大text_no,n単語が属する文再取得
                            i=0
                            max_text_no=1
                            sentiment_sentence.clear()
                            for token in tokens:
                                if token['text_no']==sentiment_sentence_no: 
                                    token['index_pertext']=i #ネガ文のindex振り直し
                                    i=i+1
                                    sentiment_sentence_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']]
                                    sentiment_sentence.append(dict(zip(sentiment_sentence_key,sentiment_sentence_values)))
                                if token['index']==s_idx: # n単語のindex更新
                                    s_idx_pertext=token['index_pertext']
                                if token['text_no']>max_text_no: # 最大text_no
                                    max_text_no=token['text_no']
                                    
                            ##print('text_no変更[前文につなげる]:',tokens)                        
    
                            #print('ext_predicate_lemmas:',ext_predicate_lemmas)
                            ext_predicates_tmp[len(ext_predicates_tmp):len(ext_predicates_tmp)]=ext_predicates_in_sentence
                            ext_predicate_lemmas_tmp[len(ext_predicate_lemmas_tmp):len(ext_predicate_lemmas_tmp)]=ext_predicate_lemmas #文結合後の単語の順番保持のため,述語は他の場所に退避
                            ext_predicates_in_sentence.clear()
                            ext_predicate_lemmas.clear()
                            #print('ext_predicate_lemmas_tmp:',ext_predicate_lemmas_tmp)
                            
                            continue# 再度S,V検索へ
                            
                        # 全文探しても主語が無い場合
                        elif sentiment_sentence_no==max_text_no and search_from_end:
                            #print('全文で主語見つかりません')
                            ext_subjects_in_sentence.append('None')
                            break
                        
                        # 前文がない場合,後文につなげる
                        elif sentiment_sentence_no==1 or search_from_end:
                            
                            for token in tokens:
                                if token['text_no']>sentiment_sentence_no: # 後文以降の文No.を一つ下げる
                                    token['text_no']=token['text_no']-1 
    
                            # text_no振り直し後のindex振り直しと,最大text_no,n単語が属する文再取得
                            i=0
                            max_text_no=1
                            sentiment_sentence.clear()
                            for token in tokens:
                                if token['text_no']==sentiment_sentence_no: 
                                    token['index_pertext']=i #ネガ文のindex振り直し
                                    i=i+1
                                    sentiment_sentence_values=[token['index'],token['index_pertext'],token['surface'],token['pos'],token['sub_pos'],token['lemma'],token['inflection']]
                                    sentiment_sentence.append(dict(zip(sentiment_sentence_key,sentiment_sentence_values)))
                                if token['index']==s_idx:
                                    s_idx_pertext=token['index_pertext']
                                if token['text_no']>max_text_no:
                                    max_text_no=token['text_no']
                                        
                            ##print('text_no変更[後文につなげる]:',tokens)
                                       
                                    
                            #print('ext_predicate_lemmas:',ext_predicate_lemmas)
                            ext_predicates_tmp[len(ext_predicates_tmp):len(ext_predicates_tmp)]=ext_predicates_in_sentence
                            ext_predicate_lemmas_tmp[len(ext_predicate_lemmas_tmp):len(ext_predicate_lemmas_tmp)]=ext_predicate_lemmas #文結合後の単語の順番保持のため,述語は他の場所に退避
                            ext_predicates_in_sentence.clear()
                            ext_predicate_lemmas.clear()
                            #print('ext_predicate_lemmas_tmp:',ext_predicate_lemmas_tmp)
                            
                            search_from_end=True #文後方結合フラグ立てる
                            
                            continue# 再度S,V検索へ
                            
                        
                    else: #主語があれば検索終了
                        break
                    
                    if k + 1 == text_num: # 全文探しても主語がない場合(現状for文内で必ず主語が見つかるかNoneになるが、想定外のエラー時のため。)
                        ext_subjects_in_sentence.append('None')
            
                
        else: #n単語の品詞が名詞,動詞,形容詞,形容動詞以外
            ext_subjects_in_sentence.append('None')
            ext_predicates_in_sentence.append('None')

 #文結合した場合,退避した述語を結合                   
        if len(ext_predicates_tmp)!=0: 
            ext_predicates_in_sentence[len(ext_predicates_in_sentence):len(ext_predicates_in_sentence)]=ext_predicates_tmp
            ext_predicate_lemmas[len(ext_predicate_lemmas):len(ext_predicate_lemmas)]=ext_predicate_lemmas_tmp
            
        ext_subjects_in_text.append(copy.copy(ext_subjects_in_sentence))
        ext_predicates_in_text.append(copy.copy(ext_predicates_in_sentence))

## 2.以降未実装

        # n単語ごとの検索が終わるごとにn_subject,n_predicateはリセット、次のN単語へ
        ext_subjects_in_sentence.clear()
        ext_predicates_in_sentence.clear()
        ext_subject_lemmas.clear()
        ext_predicate_lemmas.clear()
        ext_predicates_tmp.clear()
        ext_predicate_lemmas_tmp.clear()
        search_from_end=False
        polarity_by_sentiment.append(polarity)

    sentiment_reasons=[] # ext_subjects_in_text,ext_predicates_in_textを辞書型に変換して返却
    keys = ['subject','predicates','sentiment_type']
    for ext_subjects_in_sentence,ext_predicates_in_sentence,polarity in zip(ext_subjects_in_text,ext_predicates_in_text,polarity_by_sentiment):
        values = [ext_subjects_in_sentence,ext_predicates_in_sentence,polarity]
        sentiment_reasons.append(dict(zip(keys, values)))
        
    return sentiment_reasons



def extract_reason_records(processed_reviews: list[dict]) -> list[dict]:

    all_reasons = []

    for review in processed_reviews:
        reasons = extract_reason_pairs(review['tokens'])
        all_reasons.append(reasons)

    return all_reasons

