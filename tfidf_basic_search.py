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
import numpy as np
from collections import defaultdict
import string
from preprocess import *
import datetime
import csv
from sklearn.metrics import classification_report

# # Basic search system (baseline)
# This is a baseline search system including tfidf and cosine similarity 

# In[101]:


class BasicSearch:
    """Basic search using tfidf and cosine similarity """
    def __init__(self, search_keys, varname):
        """Define varibles."""
        self.path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/'
        self.search_keys = search_keys
        self.variable = varname

    def load_data(self, filename):
        """Load meta data."""
        dataframe = pd.read_csv(self.path + filename)
        return dataframe

    def very_simple_preprocess(self, data):
        """Simple text process: lower case only. """
        

        mydict = lambda: defaultdict(mydict)
        cleaned = mydict()
        # stem words
        for k, v in data.items():
            sent = v[self.variable]
            sent = str(sent)
            cleaned[k]['processed_text'] = sent
            cleaned[k]['sha'] = v['sha']
            cleaned[k]['title'] = v['title']

        return cleaned

    def tf_idf(self, search_keys, dataframe, varname):
        """Compute search query weights and tfidf weights."""
        tfidf_vectorizer = TfidfVectorizer()
        tfidf_weights_matrix = tfidf_vectorizer.fit_transform(dataframe[varname].values.astype('U'))
        search_query_weights = tfidf_vectorizer.transform([self.search_keys])

        return search_query_weights, tfidf_weights_matrix

    def cos_similarity(self, search_query_weights, tfidf_weights_matrix):
        """Compute cosine similarity between weights """
        cosine_distance = cosine_similarity(search_query_weights, tfidf_weights_matrix)
        similarity_list = cosine_distance[0]

        return similarity_list

    def most_similar(self, dataframe, similarity_list):
        """Return entries with cosine similarity > 0 """
        dataframe['cos_similarity'] = similarity_list
        dataframe = dataframe.loc[dataframe['cos_similarity'] > 0]
        sort_df = dataframe.sort_values(by=['cos_similarity'], ascending=False)
        
        return sort_df

    def get_similarity(self, dataframe, similarity_list):
        """Return entries with cosine similarity > 0 """
        dataframe['cos_similarity'] = similarity_list
        #dataframe = dataframe.loc[dataframe['cos_similarity'] > 0]
        sort_df = dataframe.sort_values(by=['cos_similarity'], ascending=False)
        
        return sort_df


    def most_similar_top_n(self, dataframe, similarity_list, top_n):
        """Return top n simialr entries"""
        dataframe['cos_similarity'] = similarity_list
        sort_df = dataframe.sort_values(by=['cos_similarity'], ascending=False)
        selected_df = sort_df.head(top_n)

        # most_similar = {}
        # for idx, num in enumerate(similarity_list):
        #     if num > 0:
        #         most_similar[idx] = num
        return selected_df

    def get_search_result(self):
        """Get search resutls. """
        df = self.load_data()
        search_query_weights, tfidf_weights_matrix = self.tf_idf(self.search_keys, df, 'abstract')
        similarity_list = self.cos_similarity(search_query_weights, tfidf_weights_matrix)

        c = self.most_similar(similarity_list, min_talks=1)
        df['index'] = df.index

        result_id = pd.DataFrame(c)
        result_id.rename(columns={result_id.columns[0]: "index" }, inplace = True)

        result = result_id.merge(df, on='index', how='inner')
        #add filter title
        result.to_csv(self.path + 'tfidf_search.csv')
        return result

    def convert_result_to_dict(self):
        """Convert result to dictionary. """
        result = self.get_search_result()
        mydict = lambda: defaultdict(mydict)
        result_data_dict = mydict()

        for cord_uid, abstract, title, sha in zip(result['cord_uid'], result['abstract'], result['title'], result['sha']):
            result_data_dict[cord_uid]['title'] = title
            result_data_dict[cord_uid]['abstract'] = abstract
            result_data_dict[cord_uid]['sha'] = sha

        return result_data_dict


    def simple_preprocess(self, result):
        """Simple text process: lower case, remove punc. """
        mydict = lambda: defaultdict(mydict)
        cleaned = mydict()
        for k, v in result.items():
            sent = v[self.variable]
            sent = str(sent).lower().translate(str.maketrans('', '', string.punctuation))
            cleaned[k]['processed_text'] = sent
            cleaned[k]['sha'] = v['sha']
            cleaned[k]['title'] = v['title']
            cleaned[k]['abstract'] = v[self.variable]

        return cleaned

    def extract_relevant_sentences(self, search_keywords, filter_title=None):
        """Extract sentences contain keyword in relevant articles. """
        #here user can also choose whether they would like to only select title contain covid keywords
        result_data_dict = self.convert_result_to_dict()
        processed_result = self.simple_preprocess(result_data_dict)

        mydict = lambda: defaultdict(mydict)
        sel_sentence = mydict()
        filter_w =  ['covid19','ncov','2019-ncov','covid-19','sars-cov','wuhan']
        
        for k, v in processed_result.items():
            keyword_sentence = []
            sentences = v['abstract'].split('.')
            for sentence in sentences:
                # for each sentence, check if keyword exist
                # append sentences contain keyword to list
                keyword_sum = sum(1 for word in search_keywords if word in sentence.lower())
                if keyword_sum > 0:
                    keyword_sentence.append(sentence)

            # store results
            if not keyword_sentence:
                pass
            elif filter_title is not None:
                for f in filter_w:
                    title = v['title'].lower().translate(str.maketrans('', '', string.punctuation))
                    abstract = v['abstract'].lower().translate(str.maketrans('', '', string.punctuation))
                    if (f in title) or (f in abstract):
                        sel_sentence[k]['sentences'] = keyword_sentence
                        sel_sentence[k]['sha'] = v['sha']
                        sel_sentence[k]['title'] = v['title']
            else:
                sel_sentence[k]['sentences'] = keyword_sentence
                sel_sentence[k]['sha'] = v['sha']
                sel_sentence[k]['title'] = v['title']

        print('{} articles are relevant to the topic you choose'.format(len(sel_sentence)))

        path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_2/search_results/'
        df = pd.DataFrame.from_dict(sel_sentence, orient='index')
        df.to_csv(path + 'tfidf_results_{}.csv'.format(search_keywords))
        sel_sentence_df = pd.read_csv(path + 'tfidf_results_{}.csv'.format(search_keywords))
        return sel_sentence, sel_sentence_df


class Evaluation:
    """This class evaluates precision and recall at k"""

    def __init__(self, evafile, outputname):
        """Define varibles."""
        self.path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
        self.result = evafile
        self.keyword = outputname
      
    def evaluation_k(self, sort_df, k, test_collection):
        '''get precision and recall at k'''
        # sort dictionary
        top_k = sort_df.head(k)
        top_k['system_label'] = 1
        #top_k.rename(columns={top_k.columns[0]: "cord_uid"}, inplace = True)
        # merge search result with all
        test_collection['human_label'] = np.random.choice([0, 1], size=len(test_collection))
        test_collection = test_collection[['cord_uid', 'human_label']]
        all_label = top_k.merge(test_collection, how='outer')
        #assign search result as 1
        all_label['system_label'] = all_label['system_label'].fillna(0)
        #random assign true label
        report = classification_report(all_label['human_label'], all_label['system_label'], output_dict=True)
        return report


    def evaluation(self, outputname):
        sr = BasicSearch('wear mask', 'abstract')
        test_collection = sr.load_data()
        result = pd.read_csv(self.path + self.result)
        sort_df = result.sort_values(by=['cos_similarity'], ascending=False)

        file_exists = os.path.isfile(self.path + '/result/evaluation_k_{}_basic.csv'.format(self.keyword))
        f = open(path + '/result/evaluation_k_{}_basic.csv'.format(self.keyword), 'a')
        writer_top = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        if not file_exists:
            writer_top.writerow(['k'] + ['report'] + ['time'])

        plot_precision = []
        plot_recall = []
        k_l = []
        for k in range(1, 101):
            report = self.evaluation_k(sort_df, 1, test_collection)

            f = open(self.path + '/result/evaluation_k_{}_basic.csv'.format(self.keyword), 'a')
            result_row = [[k, pd.DataFrame(report), str(datetime.datetime.now())]]
            writer_top.writerows(result_row)

            f.close()
            plot_precision.append(report['weighted avg']['precision'])
            plot_recall.append(report['weighted avg']['recall'])
            k_l.append(k)

        plot_result = pd.DataFrame(list(zip(plot_precision, k_l, plot_recall)))
        plot_result.rename(columns={plot_result.columns[0]: "precision"}, inplace = True)
        plot_result.rename(columns={plot_result.columns[1]: "k"}, inplace = True)
        plot_result.rename(columns={plot_result.columns[2]: "recall"}, inplace = True)
        plot_result.to_csv(path + 'result/{}.csv'.format(outputname))

        return plot_result

# ### Now we retrieve the data for baseline model

# In[102]:

if __name__ == "__main__":
    #s = BasicSearch('wear mask', 'abstract') #enter query
    #result = s.extract_relevant_sentences(['mask']) #extract sentence contain this keyword

    sr = BasicSearch('wear mask', 'abstract')
    test_collection = sr.load_data()
    search_query_weights, tfidf_weights_matrix = sr.tf_idf(sr.search_keys, test_collection, 'abstract')
    similarity_list = sr.cos_similarity(search_query_weights, tfidf_weights_matrix)
    #here we obtain cosine similarity > 0
    c = sr.most_similar(test_collection, similarity_list)
    c.to_csv(sr.path + 'test.csv')


    path = '/afs/inf.ed.ac.uk/user/s16/s1690903/share/cov19_scripts/'
    eva = Evaluation('test.csv', 'mask2')
    plot_result = eva.evaluation('plot_eva_basic.csv')




# # In[103]:


# s = BasicSearch('coronavirus disappear in summer', 'abstract') #enter query
# result = s.extract_relevant_sentences(['summer']) #extract sentence contain this keyword


# # In[104]:


# s = BasicSearch('incubation period', 'abstract') #enter query
# result = s.extract_relevant_sentences(['incubation', 'day'], 'title') #extract sentence contain this keyword and title mention covid


# # In[107]:


# s = BasicSearch('asymptomatic patients contagious', 'abstract') #enter query
# result = s.extract_relevant_sentences(['asymptomatic'], 'title') #extract sentence contain this keyword and title mention covid


# # ## matching labeled data to baseline result




