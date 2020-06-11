# -*- coding: utf-8 -*-

import numpy as np
from flask import Flask, request, jsonify, render_template
import pickle
#--Crawler--#
import requests
import time
import os
import csv
import sys
import json
import random
from bs4 import BeautifulSoup
import importlib
importlib.reload(sys)
#--Sentiment Analysis--#
import pandas as pd
import numpy as np
from statistics import median
import math
from snownlp import SnowNLP
from langdetect import detect
from langdetect import detect_langs
from googletrans import Translator
import pynlpir
import re

app = Flask(__name__)
model = pickle.load(open('xgBoostModel.pkl', 'rb'))

#Crawler helper
headers = {
    'Cookie': 'ALF=1584093972; SCF=An2SCaE1FJZVaog_eVsnrn72M1ug0o2dB_UP-yvVuI7ObDLXFuU5xAm8ikiO0pUCGfhW5tsj0Tykhkg6xc-wgSU.; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFSc088.bEQK8QYlOPZrimQ5JpX5KMhUgL.FozcSKq01KeE1K22dJLoIEXLxK.L1KBLBo-LxK.L1KBLBo-LxKBLBonL1-eLxKBLBonL1-eLxK.L1KBLBo-t; SUB=_2A25zR75yDeRhGeRI7lQS-S3Owj2IHXVQy8I6rDV6PUJbkdANLVbRkW1NUrBmuWsrBboCnPmkZtK6SZIiDUUepweK; SUHB=0Ryrm7dZkcYAn1; _T_WM=96104769326; WEIBOCN_FROM=1110006030; MLOGIN=1; XSRF-TOKEN=01d4e3; M_WEIBOCN_PARAMS=oid%3D4456678441554209%26luicode%3D20000061%26lfid%3D4431205229197480%26uicode%3D20000061%26fid%3D4456678441554209',
    'Referer': 'https://m.weibo.cn/detail/4479605810971990',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

def get_page(url, max_id, id_type):
    params = {
        'max_id': max_id,
        'max_id_type': id_type
    }
    try:
        r = requests.get(url, params=params, headers=headers)
        if r.status_code == 200:
            return r.json()
    except requests.ConnectionError as e:
        print('error', e.args)

def parse_page(jsondata):
    if str(jsondata) is not "None":
        pagedata = []
        datas = jsondata.get('data').get('data')
        for data in datas:
            follower_count = data.get("user").get("followers_count")
            following_count = data.get("user").get("follow_count")
            posts_count = data.get("user").get("statuses_count")
            urank = data.get("user").get("urank")
            verified = data.get("user").get("verified_type")
            user_description = data.get("user").get("description")
            like_count = data.get("like_count")
            floor_number = data.get("floor_number")
            username = data.get("user").get("screen_name")
            uid = data.get("user").get("id")
            comment = data.get("text")
            comment = BeautifulSoup(comment, 'lxml').get_text()
            pagedata.append({'UID': uid, 'Username':username, 'Follower': follower_count, 'Following': following_count, 'Original_post':posts_count, 'User_description':user_description, 'User_rank':urank, 'Verified':verified, 'Like_count':like_count, 'Floor_number':floor_number, 'Comments':json.dumps(comment,  ensure_ascii=False)})
        return pagedata
    else:
        return "None"

def comment_analysis(pagedata):
    jsondata = str(pagedata)
    df = pd.DataFrame(eval(jsondata))
    df = df.drop_duplicates()
    #Constuct Features
    ud = []
    ff = []
    fo = []
    for i in range(0,len(df)):
        try:
            #trim Comments
            s = df.loc[i, "Comments"]
            df.loc[i, "Comments"] = s[1:len(s)-1]
            #drop rows with pure repost
            if(df.loc[i, "Comments"] == "转发微博"):
                df = df.drop(i)
            else:
                if("回复@" in df.loc[i, "Comments"]):
                    s = df.loc[i, "Comments"]
                    df.loc[i, "Comments"] = s[s.index(':')+1:len(s)]

                #label user description attribute
                if(str(df.loc[i, "User_description"]) == "nan"):
                    ud.append(0)
                else:
                    ud.append(1)

                #label verified user attribute
                if(df.loc[i, "Verified"] == 0):
                    df.loc[i, "Verified"] = 1
                elif(df.loc[i, "Verified"] == -1):
                    df.loc[i, "Verified"] = 0

                #calculate follower/following and follower/originalPost ratio
                if df.loc[i, "Follower"] == 0:
                    df.loc[i, "Follower"] = 1
                ff.append(df.loc[i, "Following"] / df.loc[i, "Follower"])
                fo.append(df.loc[i, "Original_post"] / df.loc[i, "Follower"])
        except KeyError:
            ud.append(-1)
            ff.append(-1)
            fo.append(-1)

    df = df.reset_index(drop=True)
    #add features from post/user information
    df['description'] = ud
    df['ffRatio'] = ff
    df['foRatio'] = fo
    for i in range(0,len(df)):
        if df.loc[i, "description"] == -1:
            df = df.drop(i)
            ud.remove(-1)
            ff.remove(-1)
            fo.remove(-1)

    df = df.reset_index(drop=True)

    
    #Append Sentiment Score
    pynlpir.open()
    segPosts = []
    sentiScore = []
    translator = Translator()
    r = '[’！？：；【】，《》!"#$%&\'()（）“”…*+,-./:;<=>?@[\\]^_`{|}~]+'
    #Append Sentiment Score for all Comments under original post
    for i in range(0,len(df)):
        df.loc[i, "Comments"] = re.sub(r, '', df.loc[i, "Comments"])
        try:
            if "en" in str(detect(df.loc[i, "Comments"])):
                transText = str(translator.translate(df.loc[i, "Comments"], src = 'en', dest = 'zh-cn').text)
                line = transText.strip()
                s = SnowNLP(line)
                senti = (s.sentiments + SnowNLP(re.sub("[0-9]", "", line)).sentiments) / 2
                sentiScore.append(senti)
                seg = pynlpir.segment(line, pos_tagging=False)
                segPosts.append(seg)
            elif "zh-cn" or "zh-tw" or "ko" in str(detect(df.loc[i, "Comments"])):
                line = df.loc[i, "Comments"].strip()
                s = SnowNLP(line)
                senti = (s.sentiments + SnowNLP(re.sub("[0-9]", "", line)).sentiments) / 2
                sentiScore.append(senti)
                seg = pynlpir.segment(line, pos_tagging=False)
                segPosts.append(seg)
            else:
                #drop rows without valid sentiment scores
                print("error1")
                df = df.drop(i)
        except:
            print("error2")
            df = df.drop(i)

    df = df.reset_index(drop=True)
    df['Sentiment'] = sentiScore
    df = df.drop('Follower', axis=1).drop('Following', axis=1).drop('User_description', axis=1).drop('Original_post', axis=1).drop("Comments", axis = 1).drop("Username", axis=1).drop("UID", axis=1)
    pd.set_option('display.max_rows', 400)
    df = df.round({'Sentiment': 5})

    return df

def predict(df):
    dflist = df.to_numpy()
    predTestX = dflist[: ,[0,3,5,6,7]]
    predResult = model.predict(predTestX)
    troll = np.array(predResult.tolist(), dtype=np.int32)
    return troll.tolist()

#Flask REST functions
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/detection',methods=['POST'])
def detection():
    url = [str(x) for x in request.form.values()]
    print(url)
    url = url[0]
    page = page = get_page(url, 0, 0)
    if "max_id=" in url:
        maxId = url[url.index('max_id'):url.index('max_id')+15]
        page = get_page(url, maxId, 0)

    procPageData = parse_page(page)
    predictData = comment_analysis(procPageData)
    trollResult = predict(predictData)

    return jsonify(trollResult)
    #return render_template('index.html', comment_content=trollResult)#'Here is the detail: ' + page)

@app.route('/detectRender',methods=['POST'])
def detectRender():
    url = [str(x) for x in request.form.values()]
    print(url)
    url = url[0]
    page = page = get_page(url, 0, 0)
    if "max_id=" in url:
        maxId = url[url.index('max_id'):url.index('max_id')+15]
        page = get_page(url, maxId, 0)

    procPageData = parse_page(page)
    predictData = comment_analysis(procPageData)
    trollResult = predict(predictData)

    #return jsonify(trollResult)
    return render_template('index.html', comment_content=trollResult)#'Here is the detail: ' + page)

@app.route('/results',methods=['POST'])
def results():

    data = request.get_json(force=True)
    prediction = model.predict([np.array(list(data.values()))])

    output = prediction[0]
    return jsonify(output)

@app.route('/hello',methods=['POST'])
def hello():
    #return jsonify("hello")
    return "hello"
if __name__ == "__main__":
    app.run(debug=True)#ssl_context='adhoc',