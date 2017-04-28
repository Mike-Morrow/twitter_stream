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


#---------------------------------------Twitter-Credentials---------------------------------------
access_token = "493703789-Of371hUFUqIQ6Gbi3NpiyLuMGUKiBTvCO2pixasI"
access_token_secret = "Is3QLUaGEpBsK7PQBNodIbvOMRxRo1HqAPowlniJVPFQl"
consumer_key = "tY562TE1qaAdmHRpeHkHl6CmX"
consumer_secret = "Iga6f7TSeIWgTs16afhJnIfqNPDFodyaQdcCcf2yhrH4fevt34"


#---------------------------------------SQLITE-----------------------------------------------------
#establish connection to database. If db doesn't exist, sqlite will create it 
conn = sqlite3.connect('twitter_test.db', check_same_thread=False)

#create tweets table if it isn't already there
conn.execute('CREATE TABLE IF NOT EXISTS tweets(tweet_text blob, dt datetime default current_timestamp)')


#----------------------------------Custom-Twitter-Listener------------------------------------------

#we are constantly streaming tweets into our sqlite table 
class StdOutListener(StreamListener):

    def on_data(self, data):
        tweet_text = json.loads(data)
        
        #this will be a tuple with the count in the 0th slot
        count_of_records = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
        
        print(count_of_records)
        
        #populate the table with 100 records, after 100, we will update the oldest record so we never have 100+ records
        if count_of_records < 5000:
            try:
                conn.execute("INSERT INTO tweets(tweet_text) VALUES (?)", (tweet_text['text'],))
            except:
                pass
        else:
            try:
                conn.execute("UPDATE tweets set tweet_text = (?) WHERE dt = (SELECT min(dt) FROM tweets)",(tweet_text['text'],) )
            except:
                pass

        #commit the changes after each insert/update
        conn.commit()
        #print most_recent_tweet
        return True

    def on_error(self, status):
        print(status)

#----------------------------------------------------------------------------------------------------

if __name__ == "__main__":
	l = StdOutListener()
	auth = OAuthHandler(consumer_key, consumer_secret)
	auth.set_access_token(access_token, access_token_secret)
	stream = Stream(auth, l)
	stream.filter(track=['Kendrick'])


