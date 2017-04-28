from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

import re
import numpy as np
import pandas as pd
# import mpld3
# import matplotlib.pyplot as plt

from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream
import json
import sqlite3
# from wordcloud import WordCloud, STOPWORDS
import emoji
import subprocess

app = Flask(__name__)
app.secret_key = 'test123'
app.config['DEBUG'] = True

#---------------------------------------SQLITE-----------------------------------------------------
conn = sqlite3.connect('twitter_test.db', check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS tweets(tweet_text blob, dt datetime default current_timestamp)')

#-----------------------------------Helper-Method----------------------------------------------------------------

#---------------------Below-is-the-prep-for-text-word-cloud------------------

# def prep_blob(blob):
#     blob_edit = re.sub('#|@|,|u\'', '', blob)
#     blob_edit = re.sub("\W+"," ", blob_edit)
#     blob_edit = blob_edit.lower()

#     #split blob into list and remove stop words 
#     word_list = blob_edit.split()
#     stopwords = set(STOPWORDS)
#     stopwords.add('rt')
#     stopwords.add('says')
#     stopwords.add('t')
#     stopwords.add('co')
#     stopwords.add('https')
#     stopwords.add('http')
#     word_list = [word for word in word_list if word not in stopwords]
#     #turn list into dataframe then pivot it to see counts by word
#     word_df = pd.DataFrame()
#     word_df['Word'] = word_list
#     word_freq_series = word_df['Word'].value_counts()
#     word_freq_df = pd.DataFrame(word_freq_series)
#     word_freq_df['text'] = word_freq_df.index
#     word_freq_df['raw_size'] = word_freq_df[0]
#     word_freq_df = word_freq_df.drop(0,axis=1)

#     #scale the size column so that it makes sense with the d3 code
#     def scale_size(old_value):
#         #old_value = row['size']
#         old_value = float(old_value)
#         old_max = word_freq_df['raw_size'].max()
#         old_min = word_freq_df['raw_size'].min()
#         new_max = 150
#         new_min = 10
#         old_range = old_max - old_min
#         new_range = new_max - new_min
#         new_value =  (((old_value - old_min) * new_range) / old_range) + new_min
#         return int(new_value)

#     word_freq_df['size'] = word_freq_df['raw_size'].apply(scale_size)
#     word_freq_df = word_freq_df.drop('raw_size', axis=1)

#     #we take the dataframe and put it into the list of dicts
#     output_list = []

#     for i in zip(list(word_freq_df['text']), list(word_freq_df['size'])):
#         output_dict = {}
#         output_dict['text'] = i[0]
#         output_dict['size'] = i[1]
#         output_list.append(output_dict)

#     return str(output_list)



#---------------this is the prep for an emoji word cloud---------------

def prep_blob(blob):
    # import emoji
    emoji_list = []
    #print(emoji.UNICODE_EMOJI)
    for char in blob:
        if char in emoji.UNICODE_EMOJI:
            emoji_list.append(char)   


    # if len(emoji_list) == 0:
    #     return "[{'text':'No emojis yet. Keep refreshing', 'size':100}]"

    emoji_df = pd.DataFrame()
    emoji_df['Emoji'] = emoji_list
    emoji_freq_series = emoji_df['Emoji'].value_counts()
    emoji_freq_df = pd.DataFrame(emoji_freq_series)
    emoji_freq_df['text'] = emoji_freq_df.index
    emoji_freq_df['raw_size'] = emoji_freq_df['Emoji']
    emoji_freq_df = emoji_freq_df.drop('Emoji',axis=1)

    def scale_size(old_value):
        #old_value = row['size']
        if emoji_freq_df['raw_size'].max() == 1:
            return 150
        old_value = float(old_value)
        old_max = emoji_freq_df['raw_size'].max()
        old_min = emoji_freq_df['raw_size'].min()
        new_max = 150
        new_min = 20
        old_range = old_max - old_min
        new_range = new_max - new_min
        new_value =  (((old_value - old_min) * new_range) / old_range) + new_min
        # print(pd.isnull(old_value))
        # print(old_value)
        return int(new_value)

    emoji_freq_df['size'] = emoji_freq_df['raw_size'].apply(scale_size)
    # emoji_freq_df = emoji_freq_df.drop('raw_size', axis=1)

    output_list = []

    for i in zip(list(emoji_freq_df['text']), list(emoji_freq_df['size'])):
        output_dict = {}
        output_dict['text'] = i[0]
        output_dict['size'] = i[1]
        output_list.append(output_dict)

    emoji_freq_df = emoji_freq_df.rename(columns={'raw_size' : 'Count'})
    emoji_freq_df = emoji_freq_df.rename(columns={'text' : 'Emoji'})
    emoji_freq_df = emoji_freq_df.drop('size', axis=1)
    # emoji_freq_df = emoji_freq_df.drop('text', axis=1)
    # emoji_freq_df = emoji_freq_df.transpose()
    html_table = emoji_freq_df.to_html(index=False)
    d3_input = str(output_list)
    # return str([{'text': 'No emojis yet. Keep refreshing', 'size': 100}])
    return (d3_input, html_table)



#-------------------------Sentiment-Analysis-Prep--------------------

#this will return the sentiment mean of the emojis. Each unique emoji per tweet is assigned a score which is averaged. 
#the average of the averages is the final mean. This is done to give all tweets equal weight, 
#and to ignore multiple duplicate emojis in a single tweet

def sentiment_mean(tweet_list):
    import emoji
    #print(emoji.UNICODE_EMOJI)
    # print(tweet_list)
    text_df = pd.DataFrame()
    text_df['Text'] = tweet_list
    emoji_2d_list = []
    #print(emoji.UNICODE_EMOJI.keys())
    for index, row in text_df.iterrows():
        text = row['Text']
        #print(text)
        emoji_list = []
        # print(emoji.UNICODE_EMOJI)
        for char in str(text):
            if char in emoji.UNICODE_EMOJI:
                emoji_list.append(char)
        emoji_2d_list.append(emoji_list)
    # print(emoji_list)
    text_df['Emojis'] = emoji_2d_list
    # print(text_df)
    # print(emoji_2d_list)
    emoji_no_dup_list = []
    for i in text_df['Emojis']:
        emoji_no_dup_list.append(list(set(i)))
    #print(emoji_no_dup_list)
    emoji_no_dup_df = text_df.copy()
    emoji_no_dup_df['Emoji'] = emoji_no_dup_list

    emoji_no_dup_df = emoji_no_dup_df.drop(['Text', 'Emojis'], axis=1)
    #print(emoji_no_dup_df)
    #lets get sentiment dict 
    emoji_sentiment_df = pd.read_json('Emoji_Sentiment.json')
    sentiment_dict = {}
    for index, row in emoji_sentiment_df[['Char', 'Sentiment score[-1...+1]']].iterrows():
        sentiment_dict[row['Char']] = row['Sentiment score[-1...+1]']

    #lets assign scores from -1 to 1. If emoji not in sentiment dict, score = 0
    score_list = []
    for index, row in emoji_no_dup_df.iterrows():
        emoji_list = row['Emoji']
        score = 0.0
        if len(emoji_list) > 0:
            for emoji in emoji_list:
                if emoji in sentiment_dict.keys():
                    score = score + sentiment_dict[emoji] 
                else:
                    score = 0
            score = score/len(emoji_list)
        else:
            score = ''
        score_list.append(score)

    emoji_no_dup_df['Score'] = score_list
    final_df = emoji_no_dup_df[emoji_no_dup_df['Score'] != '']
    # print(final_df)
    #print(final_df['Score'].mean())

    return str(final_df['Score'].mean())

            

#----------------------------------VIEWS-From--the--6------------------------------------------------------------


#lets see if we can get twitter stream working with socketio






@app.route("/home", methods=['GET', 'POST'])
def index():

    return render_template('home.html')


@app.route("/stream", methods=['GET', 'POST'])
def stream_tweets():

    #get the count of all the tweets
    count_of_records = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]    
    print(count_of_records)

    #get a list of all the tweets 
    tweet_list = conn.execute("SELECT tweet_text FROM tweets").fetchall()
    #get a blob of all the tweets
    all_text = str(tweet_list)

    #we need to parse the text blob into the format d3 expects, a list of dicts 
    output_list = prep_blob(all_text)[0]

    #lets get a table of emoji freq
    html_table = prep_blob(all_text)[1]

    #get sentiment score
    sentiment_score = sentiment_mean(tweet_list)
    return render_template('wordcloud2.html', output_list=output_list, html_table=html_table, count_of_records=count_of_records, sentiment_score=sentiment_score)
  



if __name__ == "__main__":

    app.run()


    





