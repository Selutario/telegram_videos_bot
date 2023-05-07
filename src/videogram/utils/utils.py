# Created by Selutario <selutario@gmail.com>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv3

import re
import string

import videogram.utils.orm as orm
from numpy import dot
from numpy.linalg import norm
from pandas import DataFrame
from ruamel.yaml import YAML
from sklearn.feature_extraction.text import TfidfVectorizer
from videogram.utils.common import SETTINGS_PATH, settings

yaml = YAML()


def initialized():
    return settings['bot_name'] and settings['admin_usernames'] and settings['channel_id']


def store_settings(field, value):
    settings[field] = value
    with open(SETTINGS_PATH, 'w') as f:
        yaml.dump(settings, f)


def cleaner(query):
    document_test = query.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u') \
        .replace('ñ', 'n').replace('ü', 'u').replace('1', 'one').replace('2', 'two').replace('3', 'three'). \
        replace('4', 'four').replace('5', 'five').replace('6', 'six').replace('7', 'seven').replace('8', 'eight'). \
        replace('9', 'nine').replace('0', 'zero')
    # Remove Unicode
    document_test = re.sub(r'[^\x00-\x7F]+', ' ', document_test)
    # Remove Mentions
    document_test = re.sub(r'@\w+', '', document_test)
    # Lowercase the document
    document_test = document_test.lower()
    # Remove punctuations
    document_test = re.sub(r'[%s]' % re.escape(string.punctuation), ' ', document_test)
    # Lowercase the numbers
    document_test = re.sub(r'[0-9]', '', document_test)
    # Remove the doubled space
    return re.sub(r'\s{2,}', ' ', document_test)


def clean_documents(documents):
    documents_clean = []
    for key, value in documents.items():
        cleaned = cleaner(value)
        documents[key] = cleaned
        documents_clean.append(cleaned)

    return documents_clean


def create_df(documents):
    vt = TfidfVectorizer()  # It fits the data and transform it as a vector
    x = vt.fit_transform(documents)  # Convert the X as transposed matrix
    x = x.T.toarray()  # Create a DataFrame and set the vocabulary as the index
    return DataFrame(x, index=vt.get_feature_names_out()), vt


def get_similar_videos(q, df, vt, n_videos, sensitivity=settings['sensitivity']):
    if n_videos:
        q = [q]
        result = []
        q_vec = vt.transform(q).toarray().reshape(df.shape[0], )
        sim = {}  # Calculate the similarity

        for i in range(n_videos):
            try:
                sim[i] = dot(df.loc[:, i].values, q_vec) / norm(df.loc[:, i]) * norm(q_vec)
            except ZeroDivisionError:
                pass

        # Sort the values
        sim_sorted = sorted(sim.items(), key=lambda x: x[1], reverse=True)
        for k, v in sim_sorted:
            if v > sensitivity:
                result.append(k)
        return result


class VideosInfo:
    def __init__(self):
        # Full video items from the DB
        self.videos_info_list = []

        # Description field
        self.desc_list = []
        self.desc_df = None
        self.desc_vt = None

        # Description + keywords fields
        self.desc_kwds_list = []
        self.desc_kwds_df = None
        self.desc_kwds_vt = None

        self.update_model()

    def update_model(self):
        videos = orm.session.query(orm.VideoData).all()

        if videos:
            self.videos_info_list = videos
            self.desc_list = []
            self.desc_kwds_list = []

            for video in videos:
                self.desc_list.append(cleaner(video.description))
                self.desc_kwds_list.append(cleaner(video.description + ' ' + video.keywords))

            self.desc_df, self.desc_vt = create_df(self.desc_list)
            self.desc_kwds_df, self.desc_kwds_vt = create_df(self.desc_kwds_list)

    def __len__(self):
        return len(self.videos_info_list)


videos_info = VideosInfo()
