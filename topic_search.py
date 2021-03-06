import pandas as pd 
from collections import defaultdict
import string
from gensim.models import CoherenceModel
import gensim
from pprint import pprint
import spacy,en_core_web_sm
from nltk.stem import PorterStemmer
import os
import json
from gensim.models import Word2Vec
import nltk
import re
import collections
from sklearn.metrics import cohen_kappa_score
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import classification_report
import numpy as np
from collections import defaultdict
import string
from preprocess import *
import datetime
import csv
from tfidf_basic_search import *
import gc
import os
from topic_model import *



# ## Using LDA to rank documents
# LDA is optimized by coherence score u_mass



class LDATopic:
    def __init__(self, processed_text, topic_num, alpha, eta):
        """Define varibles."""
        self.path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
        self.text = processed_text
        self.topic_num = topic_num
        self.alpha = alpha
        self.eta = eta

    def get_lda_score_eval(self, dictionary, bow_corpus):
        """LDA model and coherence score."""

        lda_model = gensim.models.ldamodel.LdaModel(bow_corpus, num_topics=self.topic_num, id2word=dictionary, passes=10,  update_every=1, random_state = 300, alpha=self.alpha, eta=self.eta)
        #pprint(lda_model.print_topics())

        # get coherence score
        cm = CoherenceModel(model=lda_model, corpus=bow_corpus, coherence='u_mass')
        coherence = cm.get_coherence()
        print('coherence score is {}'.format(coherence))

        return lda_model, coherence

    def get_score_dict(self, bow_corpus, lda_model_object):
        """
        get lda score for each document
        """
        all_lda_score = {}
        for i in range(len(bow_corpus)):
            lda_score ={}
            for index, score in sorted(lda_model_object[bow_corpus[i]], key=lambda tup: -1*tup[1]):
                lda_score[index] = score
                od = collections.OrderedDict(sorted(lda_score.items()))
            all_lda_score[i] = od
        return all_lda_score


    def topic_modeling(self):
        """Get LDA topic modeling."""
        # generate dictionary
        dictionary = gensim.corpora.Dictionary(self.text.values())
        bow_corpus = [dictionary.doc2bow(doc) for doc in self.text.values()]
        # modeling
        model, coherence = self.get_lda_score_eval(dictionary, bow_corpus)

        lda_score_all = self.get_score_dict(bow_corpus, model)

        all_lda_score_df = pd.DataFrame.from_dict(lda_score_all)
        all_lda_score_dfT = all_lda_score_df.T
        all_lda_score_dfT = all_lda_score_dfT.fillna(0)

        return model, coherence, all_lda_score_dfT, bow_corpus

    def get_ids_from_selected(self, text):
        """Get unique id from text """
        id_l = []
        for k, v in text.items():
            id_l.append(k)
            
        return id_l





# Now we extract articles contain the most relevant topic

def selected_best_LDA(path, data, varname, num_topic):
        """Select the best lda model with extracted text """
        # convert data to dictionary format
        file_exists = os.path.isfile(path + 'result/lda_result.csv')
        f = open(path + 'result/lda_result.csv', 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['a'] + ['b'] + ['coherence'] + ['time'] +['topics'] + ['num_topics'] )

        m = MetaData(data)
        metaDict = m.data_dict()

        #process text and extract text with keywords
        et = ExtractText(metaDict, 'anything', varname) #doesn't matter
        text1 = et.simple_preprocess()

        #text1 = et.extract_w_keywords()

        # extract nouns, verbs and adjetives
        text = et.get_noun_verb2(text1)

        # optimized alpha and beta
        alpha = [0.1, 0.3, 0.5, 0.7, 0.9]
        beta = [0.1, 0.3, 0.5, 0.7, 0.9]

        # alpha = [0.3]
        # beta = [0.3]

        mydict = lambda: defaultdict(mydict)
        cohere_dict = mydict()
        for a in alpha:
            for b in beta:
                lda = LDATopic(text, num_topic, a, b)
                model, coherence, scores, corpus = lda.topic_modeling()
                cohere_dict[coherence]['a'] = a
                cohere_dict[coherence]['b'] = b

                
        # sort result dictionary to identify the best a, b
        # select a,b with the largest coherence score 
        sort = sorted(cohere_dict.keys())[0] 
        a = cohere_dict[sort]['a']
        b = cohere_dict[sort]['b']
        
        # run LDA with the optimized values
        lda = LDATopic(text, num_topic, a, b)
        model, coherence, scores_best, corpus = lda.topic_modeling()
        #pprint(model.print_topics())

        #f = open(path + 'result/lda_result.csv', 'a')
        result_row = [[a, b, coherence, str(datetime.datetime.now()), model.print_topics(), num_topic]]
        writer_top.writerows(result_row)

        f.close()
        gc.collect()
       
        # select merge ids with the LDA topic scores 
        # store result model with the best score
        id_l = lda.get_ids_from_selected(text)
        scores_best['cord_uid'] = id_l 

        # get topic dominance
        t = LDATopicModel()
        df_topic_sents_keywords = t.format_topics_sentences(model, corpus)
        df_dominant_topic = df_topic_sents_keywords.reset_index()
        #print(df_dominant_topic.shape)

        sent_topics_df = pd.concat([df_dominant_topic, scores_best], axis=1)
        #sent_topics_df = sent_topics_df[['Dominant_Topic', 'Perc_Contribution', 'Topic_Keywords']]

        return sent_topics_df
        

def selected_best_LDA_allw(path, data, varname, num_topic):
        """Select the best lda model with extracted text """
        # convert data to dictionary format
        file_exists = os.path.isfile(path + 'result/lda_result.csv')
        f = open(path + 'result/lda_result.csv', 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['a'] + ['b'] + ['coherence'] + ['time'] +['topics'] + ['num_topics'] )

        m = MetaData(data)
        metaDict = m.data_dict()

        #process text and extract text with keywords
        et = ExtractText(metaDict, 'anything', varname) #doesn't matter
        text = et.simple_preprocess()

       
        text = et.preprocess_cluster_sentence(text)

        # optimized alpha and beta
        # alpha = [0.1, 0.3, 0.5, 0.7, 0.9]
        # beta = [0.1, 0.3, 0.5, 0.7, 0.9]

        alpha = [0.1]
        beta = [0.1]

        mydict = lambda: defaultdict(mydict)
        cohere_dict = mydict()
        for a in alpha:
            for b in beta:
                lda = LDATopic(text, num_topic, a, b)
                model, coherence, scores, corpus = lda.topic_modeling()
                cohere_dict[coherence]['a'] = a
                cohere_dict[coherence]['b'] = b

                
        # sort result dictionary to identify the best a, b
        # select a,b with the largest coherence score 
        sort = sorted(cohere_dict.keys())[0] 
        a = cohere_dict[sort]['a']
        b = cohere_dict[sort]['b']
        
        # run LDA with the optimized values
        lda = LDATopic(text, num_topic, a, b)
        model, coherence, scores_best, corpus = lda.topic_modeling()
        #pprint(model.print_topics())

        #f = open(path + 'result/lda_result.csv', 'a')
        result_row = [[a, b, coherence, str(datetime.datetime.now()), model.print_topics(), num_topic]]
        writer_top.writerows(result_row)

        f.close()
        gc.collect()
       
        # select merge ids with the LDA topic scores 
        # store result model with the best score
        id_l = lda.get_ids_from_selected(text)
        scores_best['cord_uid'] = id_l 

        # get topic dominance
        t = LDATopicModel()
        df_topic_sents_keywords = t.format_topics_sentences(model, corpus)
        df_dominant_topic = df_topic_sents_keywords.reset_index()
        #print(df_dominant_topic.shape)

        sent_topics_df = pd.concat([df_dominant_topic, scores_best], axis=1)
        #sent_topics_df = sent_topics_df[['Dominant_Topic', 'Perc_Contribution', 'Topic_Keywords']]

        return sent_topics_df



# here we select the text with the most relevant topic according to the LDA result
def select_text_from_LDA_results(file, keyword, varname, scores_best):
        # choose papers with the most relevant topic
        # convert data to dictionary format
        m = MetaData(file)
        metaDict = m.data_dict()

        # process text and extract text with keywords
        et = ExtractText(metaDict, keyword, varname)
        # extract text together with punctuation
        #text1 = et.extract_w_keywords_punc()
        text1 = et.very_simple_preprocess()
        # need to decide which topic to choose after training
        #sel = scores_best[scores_best[topic_num] > 0] 
        sel = scores_best
        
        count = 0
        mydict = lambda: defaultdict(mydict)
        selected = mydict()
        for k, v in text1.items():
            if k in sel.cord_uid.tolist():
                selected[k]['title'] = v['title']
                selected[k]['processed_text'] = v['processed_text']
                selected[k]['sha'] = v['sha']
                selected[k]['cosine_similarity'] = v['cos_similarity']

                # get topic dominance
                percent = sel.loc[sel.cord_uid == k, 'Perc_Contribution']
                dominance = sel.loc[sel.cord_uid == k, 'Dominant_Topic']
                #print(percent[percent.index[0]])

                selected[k]['Perc_Contribution'] = percent[percent.index[0]]
                selected[k]['Dominant_Topic'] = dominance[dominance.index[0]]


        print ("There are {} abstracts selected". format(len(selected)))
        return selected

def extract_relevant_sentences(cor_dict, search_keywords, filter_title=None):
    """Extract sentences contain keyword in relevant articles. """
    #here user can also choose whether they would like to only select title contain covid keywords

    mydict = lambda: defaultdict(mydict)
    sel_sentence = mydict()
    filter_w = ['covid19', '2019-ncov', 'covid-19', 'sars-cov-2', 'wuhan']
    
    for k, v in cor_dict.items():
        keyword_sentence = []
        sentences = v['processed_text'].split('.')
        for sentence in sentences:
            # for each sentence, check if keyword exist
            # append sentences contain keyword to list
            keyword_sum = sum(1 for word in search_keywords if word in sentence)
            if keyword_sum > 0:
                keyword_sentence.append(sentence)         

        # store results
        if not keyword_sentence:
            pass
        elif filter_title is not None:
            title = v['title'].lower().translate(str.maketrans('', '', string.punctuation))
            abstract = v['processed_text'].lower().translate(str.maketrans('', '', string.punctuation))
            for f in filter_w:                
                if (f in title) or (f in abstract):
                    print('y')
                    sel_sentence[k]['sentences'] = keyword_sentence
                    sel_sentence[k]['sha'] = v['sha']
                    sel_sentence[k]['title'] = v['title']
                    sel_sentence[k]['cosine_similarity'] = v['cos_similarity']
                else:
                    print('n')

        else:
            sel_sentence[k]['sentences'] = keyword_sentence
            sel_sentence[k]['sha'] = v['sha']
            sel_sentence[k]['title'] = v['title'] 
            sel_sentence[k]['cosine_similarity'] = v['cos_similarity']

            
    print('{} articles are relevant to the topic you choose'.format(len(sel_sentence)))
    return sel_sentence

def store_extract_sentences(sel_sentence, search_keywords):
    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
    df = pd.DataFrame.from_dict(sel_sentence, orient='index')
    df.to_csv(path + 'search_results_{}.csv'.format(search_keywords))
    sel_sentence_df = pd.read_csv(path + 'search_results_{}.csv'.format(search_keywords))
    return sel_sentence_df



class Evaluation:
    """This class evaluates precision and recall at k"""

    def __init__(self, evafile, outputname):
        """Define varibles."""
        self.path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
        #self.path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
        self.path2 = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
        self.result = evafile
        self.keyword = outputname
      
    def evaluation_k(self, sort_df, k, test_collection):
        '''get precision and recall at k'''
        # sort dictionary
        top_k = sort_df.head(k)
        #assign search result as 1
        top_k['system_label'] = 1
        if 'cord_uid' not in top_k.columns:
            top_k.rename(columns={top_k.columns[0]: "cord_uid"}, inplace = True)

        #merge search result with test collection
        test_collection = test_collection[['cord_uid', 'relevance']]
        all_label = top_k.merge(test_collection, how='outer')

        #assign not relevant as 0
        all_label['system_label'] = all_label['system_label'].fillna(0)
        all_label.to_csv(self.path + 'testing.csv')
        #get classification report
        report = classification_report(all_label['relevance'], all_label['system_label'], output_dict=True)
        return report


    def evaluation(self, lda_results, search_results, searchfilename, search_var, filename, datatype, topic_num):
        """Wrapping evaluation function in loop. """ #filename: annotation file

        cor_dict_mask = select_text_from_LDA_results(search_results, searchfilename, search_var, lda_results)

        result = pd.DataFrame.from_dict(cor_dict_mask, orient='index')
        result['cord_uid'] = result.index
        path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
        result.to_csv(path + 'test_selected.csv')

        sr = BasicSearch('wear mask', 'abstract')
        test_collection = sr.load_data(filename)

        #select target topic
        res = []
        for num in topic_num:
            sel_result = result[result['Dominant_Topic'] == num]
            res.append(sel_result)

        result = pd.concat(res)

        
        if 'cosine_similarity' in result.columns:
            sort_df = result.sort_values(by=['cosine_similarity', 'Perc_Contribution'], ascending=[False, False])
        else:
            sort_df = result.sort_values(by=['cos_similarity', 'Perc_Contribution'], ascending=[False, False])

        #df.sort_values(['age', 'grade'], ascending=[True, False])
        result = sort_df
        
        result.to_csv(self.path2 + 'search_results/{}_temp_eva.csv'.format(searchfilename))
        size = result.shape[0]

        file_exists = os.path.isfile(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword))
        f = open(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword), 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['k'] + ['report'] + ['time'])

        plot_precision = []
        plot_recall = []
        f1 = []
        k_l = []
        for k in range(1, size+1):
            report = self.evaluation_k(result, k, test_collection)

            f = open(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword), 'a')
            result_row = [[k, pd.DataFrame(report), str(datetime.datetime.now())]]
            writer_top.writerows(result_row)

            f.close()
            plot_precision.append(report['macro avg']['precision'])
            plot_recall.append(report['macro avg']['recall'])
            f1.append(report['macro avg']['f1-score'])
            k_l.append(k)

        plot_result = pd.DataFrame(list(zip(k_l, plot_precision, plot_recall, f1)))
        plot_result.rename(columns={plot_result.columns[1]: "precision"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[0]: "k"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[2]: "recall"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[3]: "f1_score"}, inplace=True)
        plot_result.to_csv(self.path + 'result/evaluation_plot_{}_{}.csv'.format(self.keyword, datatype))

        return plot_result, result


    def evaluation_sent_cluster(self, lda_results, search_results, searchfilename, search_var, filename, datatype, topic_num):
        """Wrapping evaluation function in loop.
        filename: annotation file
        topic_num: topics that you need to remove 
        datatype: distinguisted the outputfile name, is it tfidf or topic
        """ 
        
        cor_dict_mask = select_text_from_LDA_results(search_results, searchfilename, search_var, lda_results)

        result = pd.DataFrame.from_dict(cor_dict_mask, orient='index')
        result['cord_uid'] = result.index
        path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
        result.to_csv(path + 'test_selected.csv')

        sr = BasicSearch('wear mask', 'abstract')
        test_collection = sr.load_data(filename)
        
        #select target topic and put them at the back, here we want to put the dominant topics at the back
        result = result.sort_values(by=['Perc_Contribution'], ascending=[True])
        print(result.columns)

        res = []
        for num in topic_num:
            sel_result = result[result['Dominant_Topic'] == num]
            res.append(sel_result)
        poor_result = pd.concat(res)

        result = result.sort_values(by=['Perc_Contribution'], ascending=[False])

        result = result.append(poor_result)
        result = result.drop_duplicates(subset='cord_uid', keep="last")

        result.to_csv(self.path2 + 'search_results/{}_temp_eva_sent.csv'.format(searchfilename))
        size = result.shape[0]

        file_exists = os.path.isfile(self.path + '/result/evaluation_k_sent_{}.csv'.format(self.keyword))
        f = open(self.path + '/result/evaluation_k_sent{}.csv'.format(self.keyword), 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['k'] + ['report'] + ['time'])

        plot_precision = []
        plot_recall = []
        f1 = []
        k_l = []
        for k in range(1, size + 1):
            report = self.evaluation_k(result, k, test_collection)

            f = open(self.path + '/result/evaluation_k_sent_{}.csv'.format(self.keyword), 'a')
            result_row = [[k, pd.DataFrame(report), str(datetime.datetime.now())]]
            writer_top.writerows(result_row)

            f.close()
            plot_precision.append(report['macro avg']['precision'])
            plot_recall.append(report['macro avg']['recall'])
            f1.append(report['macro avg']['f1-score'])
            k_l.append(k)

        plot_result = pd.DataFrame(list(zip(k_l, plot_precision, plot_recall, f1)))
        plot_result.rename(columns={plot_result.columns[1]: "precision"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[0]: "k"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[2]: "recall"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[3]: "f1_score"}, inplace=True)
        plot_result.to_csv(self.path + 'result/evaluation_plot_{}_{}_sent.csv'.format(self.keyword, datatype))

        return plot_result, result

    def evaluation_tfidf(self, lda_results, search_results, searchfilename, search_var, filename, datatype):
        """Wrapping evaluation function in loop. """
        cor_dict_mask = select_text_from_LDA_results(search_results, searchfilename, search_var, lda_results)

        result = pd.DataFrame.from_dict(cor_dict_mask, orient='index')
        result['cord_uid'] = result.index
        path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
        result.to_csv(path + 'test_selected.csv')

        sr = BasicSearch('wear mask', 'abstract')
        test_collection = sr.load_data(filename)
        result = pd.read_csv(self.path2 + self.result)

        if 'cosine_similarity' in result.columns:
            sort_df = result.sort_values(by=['cosine_similarity'], ascending=[False])
        else:
            sort_df = result.sort_values(by=['cos_similarity'], ascending=[False])

        #df.sort_values(['age', 'grade'], ascending=[True, False])
        result = sort_df
        
        result.to_csv(self.path + 'temp_eva.csv')
        size = result.shape[0]

        file_exists = os.path.isfile(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword))
        f = open(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword), 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['k'] + ['report'] + ['time'])

        plot_precision = []
        plot_recall = []
        f1 = []
        k_l = []
        for k in range(1, size+1):
            report = self.evaluation_k(result, k, test_collection)

            f = open(self.path + '/result/evaluation_k_{}.csv'.format(self.keyword), 'a')
            result_row = [[k, pd.DataFrame(report), str(datetime.datetime.now())]]
            writer_top.writerows(result_row)

            f.close()
            plot_precision.append(report['macro avg']['precision'])
            plot_recall.append(report['macro avg']['recall'])
            f1.append(report['macro avg']['f1-score'])
            k_l.append(k)

        plot_result = pd.DataFrame(list(zip(k_l, plot_precision, plot_recall, f1)))
        plot_result.rename(columns={plot_result.columns[1]: "precision"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[0]: "k"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[2]: "recall"}, inplace=True)
        plot_result.rename(columns={plot_result.columns[3]: "f1_score"}, inplace=True)
        plot_result.to_csv(self.path + 'result/evaluation_plot_{}_{}.csv'.format(self.keyword, datatype))

        return plot_result

def basic_search(path, keywords, outputname):
    """Get tfidf search result """

    sr = BasicSearch(keywords, 'abstract')
    ps = PorterStemmer()

    test_collection = sr.load_data('test_collection.csv')
    #simple process, stemming
    test_collection['abstract'] = test_collection['abstract'].str.split(" ").apply(lambda x: [ps.stem(y) for y in x]) 
    test_collection['abstract'] = test_collection['abstract'].apply(lambda x: [' '.join(x)]) 
    test_collection['abstract'] = test_collection['abstract'].str[0]

    search_query_weights, tfidf_weights_matrix = sr.tf_idf(sr.search_keys, test_collection, 'abstract')
    similarity_list = sr.cos_similarity(search_query_weights, tfidf_weights_matrix)

    #here we obtain cosine similarity > 0
    basic_search_result = sr.most_similar(test_collection, similarity_list)
    basic_search_result.to_csv(sr.path + 'search_results/basic_search_{}.csv'.format(outputname))

    return basic_search_result

def basic_search_by_word(keywords, outputname):
        """Basic search by matching keywords, no tfidf  """
        path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
        search_results = []
        for word in keywords.split():
            #print(word)
            basic_search_file = basic_search(path, word, outputname)
            search_results.append(basic_search_file)
        all_search = pd.concat(search_results)
        all_search = all_search.drop_duplicates(subset='cord_uid', keep="last")
        all_search.to_csv(path + 'search_results/basic_search_{}.csv'.format(outputname))
        



# sr = BasicSearch('wear mask', 'abstract')
# test_collection = sr.load_data('test_collection.csv')

# ## Question 1: Is wearing mask an effective way to control pandemic?

# path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
# #basic_search_file = basic_search(path, 'wear mask', 'wear_mask')#keywords, outputname
# #scores_best_mask = selected_best_LDA(path, 'search_results/basic_search_wear_mask.csv', 'wear mask', 'abstract', 20)

# basic_search_by_word('wear mask', 'wear_mask')
# # run LDA
# scores_best_mask = selected_best_LDA(path, 'search_results/basic_search_wear_mask.csv', 'abstract', 20)

if __name__ == "__main__":


    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
    basic_search_file = basic_search(path, 'wear mask', 'wear_mask')#keywords, outputname
    scores_best_mask = selected_best_LDA(path, 'search_results/basic_search_wear_mask.csv', 'abstract', 15)

    # # get evaluation for topic search
    # path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
    eva = Evaluation('/search_results/test_selected.csv', 'mask_stem') #evaluation, test_selected.csv is result of the retrieval system
    # test collection file generated with test_collection, evaluate the top x entries
    #intermediate files, temp_eva
    #plot_result, result = eva.evaluation(scores_best_mask, 'search_results/basic_search_wear_mask.csv', 'mask', 'abstract','test_collection/labels/test_collection_mask_relabel.csv', 'topic', [2,14,0,8,13])

    plot_result, result = eva.evaluation(scores_best_mask, 'search_results/basic_search_wear_mask.csv', 'mask', 'abstract','test_collection/labels/test_collection_mask_relabel.csv', 'topic', [0,2,8,14,15])

    # get evaluation for tfidf search ********************************************
    eva = Evaluation('search_results/basic_search_wear_mask.csv', 'mask_tfidf') #evaluation, filename, test_selected.csv is result of the retrieval system
    plot_result = eva.evaluation_tfidf('test_collection/labels/test_collection_mask_relabel.csv', 'tfidf')

    # now we check which one we miss
    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
    annotation = pd.read_csv(path + 'annotation/mask_relabel.csv')
    ranked_file = pd.read_csv(path + 'temp_eva_wear_mask.csv', encoding="ISO-8859-1", engine='python')
    check_result = ranked_file.merge(annotation, on = 'textid', how = 'outer')
    check_result.to_csv(path + 'check_result.csv')

    # The advantage of the topic search is to be able to group topics despite of matching, we should apply topic not on top of tfidf 
    # retrieve result without tfidf ranking 

    basic_search_by_word('wear mask', 'wear_mask')
    # run LDA
    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
    scores_best_mask = selected_best_LDA(path, 'search_results/basic_search_wear_mask.csv', 'abstract', 25)
   
    #cor_dict_mask.update(cor_dict_mask3)
    # cor_dict_df = pd.DataFrame.from_dict(cor_dict_mask, orient='index')
    # path2 = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
    # cor_dict_df.to_csv(path2 + 'test_selected.csv')

    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
    eva = Evaluation('/search_results/test_selected.csv', 'mask_stem') #evaluation, test_selected.csv is result of the retrieval system

    plot_result, result = eva.evaluation(scores_best_mask, 'search_results/basic_search_wear_mask.csv', 'mask', 'abstract', 'test_collection/labels/test_collection_mask_relabel.csv', 'topic', [8, 1, 3])

    # use lda again on the importance sentences in the selected doc to see if can further identify stance 

    # further eliminate topics, call this system FAB fact-check academic paper boost







# # ### Annotation guidline for question 1
# # We extracted 33 papers that are supposed to discuss whether using masks is useful. We annotate  whether the key sentences suggest using mask can reduce the risk of infection.
# # 
# # #### Stance Annotation 
# # * ‘1’ sentences that support using a mask during a pandemic is useful 
# # * ‘2’  papers that assume masks as useful and examine the public’s willingness to comply the rules,
# # * ’0’ no obvious evidence that shows using mask is protective or the protection is very little
# # * '3' Not relevant to the above stance
# # 
# # #### relevance annotation
# # * '1' the result is relevent to the question  
# # * '0' the result is not relevant to the question

# # In[48]:


# #here we need to add the stats analysis 
# path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/annotation/'
# annotation_mask = pd.read_csv(path + 'wear_mask.csv')


# # In[49]:


# # view file
# annotation_mask.head(5)
# print('there are {} articles relevant to the topic'.format(annotation_mask.shape[0]))


# # * ‘1’  support using a mask during a pandemic is useful 
# # * ‘2’  assume masks as useful and examine the public’s willingness to comply the rules,
# # * ’0’ no obvious evidence that shows using mask is protective or the protection is very little
# # * '3' Not relevant to the above stance
# # 
# # result from annotator 1

# # In[289]:


# annotation_mask['stance'].value_counts()


# # result from annotator 2

# # In[290]:


# annotation_mask['stance.1'].value_counts()


# # In[59]:


# annotation_mask['stance'].value_counts()[2]


# # In[64]:


# print('there are {} papers support using a mask during a pandemic is useful, {} assume masks as useful and examine the public’s willingness to comply the rules,  {} papers show no obvious evidence that shows using mask is protective or the protection is very little'. format(str(annotation_mask['stance'].value_counts()[1]), str(annotation_mask['stance'].value_counts()[2]), annotation_mask['stance'].value_counts()[0]) )
          


# # ### inter-rater repliability 

# # In[291]:


# cohen_kappa_score(annotation_mask['stance'], annotation_mask['stance.1'])


# # In[87]:


# mask = annotation_mask['relevance'].value_counts()
# print('there are {} papers relevant to the topic, {} papers not relevant to the topic'. format(mask[1], mask[0]))


# # ### First author location

# # In[ ]:





# # ## Results
# # According to the key sentences in 33 abstract that discuss the topic of public using masks, only one paper suggests that there’s not enough evidence to show that mask is useful.
# # There are 14 papers that suggest their results show using surgical mask during a pandemic is effective in reducing infection
# # 14 paper consider public individuals using masks are necessary in reducing risks of being infect, and these paper look at whether the public are willing to comply to the rules. (X papers are from  Hong Kong, based on the region of the first author)
# # 5 papers are not relevant to the topic
# # 
# # Conclusion:
# # government in some regions advocate using masks as a standard approach to reduce risk of infection, papers in these regions focus on whether people comply to the rules. When some government advocate that there is little evidence show that mask is effective in controlling the pandemic, nearly half of the academic papers from our search result either consider wearing masks as a standard practice that the public show comply, nearly half of the papers found evidence to support that wearing masks is effective in controlling the pandemic.
# # 

# # ### Question 2: How long in incubation period? In some region (e.g. China), there’s rumour circulating that the incubation period is longer than 14 days

# # ### Annotation guideline for question 2:
# # 
# # #### stance annotation
# # Here we want to identify papers that report a result aligns with the incubation period reported by the governments
# # UK government advocate: 2-14 days, mean 5
# # * ‘1’  same as government advocate 
# # * ‘0’  different from what the government
# # *  Not relevant to the question 
# # 
# # #### relevance annotation
# # * '1' the result is relevent to the question  
# # * '2' the result is not relevant to the question

# # In[134]:


# scores_best_incu = selected_best_LDA(['incubation'], 'abstract', 30)


# # In[127]:


# scores_best_incu.shape


# # In[126]:


# # topic number 0 is most relevant to public wearing mask
# # which topic do you think is most relevant to your search
# # cor_dict_incu = select_text_from_LDA_results('incubation', 'abstract', scores_best_incu, 26)
# # print ("There are {} abstracts selected". format(len(cor_dict_incu)))
# cor_dict_incu2 = select_text_from_LDA_results('incubation', 'abstract', scores_best_incu, 9)
# print ("There are {} abstracts selected". format(len(cor_dict_incu2)))
# cor_dict_incu3 = select_text_from_LDA_results('incubation', 'abstract', scores_best_incu, 1)
# print ("There are {} abstracts selected". format(len(cor_dict_incu3)))
# cor_dict_incu.update(cor_dict_incu2)
# cor_dict_incu.update(cor_dict_incu3)
# len(cor_dict_incu)


# # In[113]:


# # extract relevant sentences  #search keywords can be a list
# sel_sentence_incu, sel_sentence_df_incu = extract_relevant_sentences(cor_dict_incu, ['day'], 'title')


# # In[103]:


# #read extracted article
# sel_sentence_df_incu.head(10)


# # ## Incubation period statistical analysis

# # In[84]:


# #here we need to add the stats analysis 
# path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/annotation/'
# annotation_incubation = pd.read_csv(path + 'incubation.csv')
# print('there are {} articles relevant to the topic'.format(annotation_incubation.shape[0]))


# # result from annotator 1

# # In[85]:


# incubation = annotation_incubation['stance'].value_counts()
# print('there are {} paper shows the incubation period is 2-14 days with mean 5 days, {} papers shows a different number'. format(incubation[0], incubation[1])
#      )


# # In[86]:


# incubation = annotation_incubation['relevance'].value_counts()
# print('there are {} papers relevant to the topic, {} papers not relevant to the topic'. format(incubation[1], incubation[0]))


# # ## Question 3: Are asymptomatic patients infectious?
# # 

# # ### Annotation guideline for question 3:
# # Here we want to identify whether asymtomatic cases contribute to the spread of the virus
# # 
# # #### stance annotation
# # * ‘1’  there is clear evidence show that asymtomatic cases contribute to the spread of the virus
# # * ‘0’  it is unlikely that asymtomatic cases contribute to the spread of the virus
# # * '3' Not relevant to the question
# # 
# # #### relevance annotation
# # * '1' the result is relevent to the question  
# # * '0' the result is not relevant to the question

# # In[62]:


# scores_best_asym = selected_best_LDA('asymptomatic', 'abstract')


# # In[63]:


# # topic number 19 is most relevant to public wearing mask
# # which topic do you think is most relevant to your search
# cor_dict_asym = select_text_from_LDA_results('asymptomatic', 'abstract', scores_best_asym, 19)
# print ("There are {} abstracts selected". format(len(cor_dict_asym)))


# # In[119]:


# # extract relevant sentences  #search keywords can be a list
# sel_sentence_asym, sel_sentence_df_asym = extract_relevant_sentences(cor_dict_asym, ['transmission'], 'title')


# # In[120]:


# sel_sentence_df_asym.tail(10)


# # ## Asymptomatic Result

# # In[78]:


# #here we need to add the stats analysis 
# annotation_asymptomatic = pd.read_csv(path + 'asymtomatic.csv')
# print('there are {} articles relevant to the topic'.format(annotation_asymptomatic.shape[0]))


# # In[79]:


# asymptomatic = annotation_asymptomatic['stance'].value_counts()
# print('{} papers show that there is clear evidence show that asymtomatic cases contribute to the spread of the virus, {} papers show that it is unlikely that asymtomatic cases contribute to the spread of the virus'.format(asymptomatic[1], asymptomatic[0]))


# # In[82]:


# asymptomatic = annotation_asymptomatic['relevance'].value_counts()
# print('there are {} papers relevant to the topic, {} papers not relevant to the topic'. format(asymptomatic[1], asymptomatic[0]))


# # ## Question 4: Will the virus disappear in the summer? 
# # 
# # ### Annotation guideline for question 4
# # * '1' the result is relevent to the question  
# # * '0' the result is not relevant to the question

# # In[255]:


# scores_best_sea = selected_best_LDA('seasonality', 'abstract')


# # In[268]:


# # topic number 19 is most relevant to publicr wearing mask
# # which topic do you think is most relevant to your search
# cor_dict_sea = select_text_from_LDA_results('season', 'abstract', scores_best_sea, 0)
# print ("There are {} abstracts selected". format(len(cor_dict_sea)))


# # In[269]:


# # extract relevant sentences  #search keywords can be a list
# sel_sentence_sea , sel_sentence_df_sea  = extract_relevant_sentences(cor_dict_sea, ['summer'])


# # In[172]:


# sel_sentence_df_sea.tail(10)


# # ## virus and temperature result

# # In[72]:


# annotation_seasonality= pd.read_csv(path + 'seasonality.csv')
# print('there are {} articles relevant to the topic'.format(annotation_seasonality.shape[0]))


# # In[76]:


# seasonality = annotation_seasonality['relevance'].value_counts()
# print('there are {} papers relevant to the topic, {} papers not relevant to the topic'. format(seasonality[1], seasonality[0]))


