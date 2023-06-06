# -*- coding: utf-8 -*-
"""
Created on Wed Oct 21 09:25:05 2015

@author: zhangchenhan
"""
#from pandas.io.data import DataReader
from datetime import datetime
from itertools import combinations
from math import log
import math
import operator
from scipy import sparse
import scipy
from string import punctuation
import sys
from time import gmtime, strftime
import time
import time

from sklearn import metrics, preprocessing, cross_validation
from sklearn import svm
from sklearn.cross_validation   import StratifiedKFold
import sklearn.decomposition
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import mean_squared_error, f1_score, precision_score, recall_score, roc_auc_score, accuracy_score
from sklearn.neighbors import RadiusNeighborsRegressor, KNeighborsRegressor
import talib
from talib.abstract import *

from ggplot import *
import matplotlib.pyplot as plt
import numpy as np 
import pandas as pd
import pyfolio as pf
import sframe as sf
import sklearn as sk
import sklearn.linear_model as lm
import tushare as ts
import xgboost as xgb
import zipline as zl
from zipline.algorithm import TradingAlgorithm


#
#from pyalgotrade import dataseries
#from pyalgotrade.technical import macd
#from pyalgotrade.technical import ma
#from pyalgotrade.technical import rsi
#from pyalgotrade.technical import cross
#from zipline.transforms.ta import EMA
#%%original data
N = 6
data = pd.read_csv('/Users/jianboxue/Documents/Research_Projects/Momentum/index_shanghai.csv',index_col = 'date',parse_dates = 'date')

#features owned by the day for predicting(include open)
data['month'] = data.index.month
data['week'] = data.index.week
data['weekofyear'] = data.index.weekofyear
data['day'] = data.index.day
data['dayofweek'] = data.index.dayofweek
data['dayofyear'] = data.index.dayofyear

donchian_channel_max = np.array([max(data['high'][max(i,20)-20:max(i,20)]) for i in range(len(data))])#the highest price in last n days
donchian_channel_min = np.array([min(data['low'][max(i,20)-20:max(i,20)]) for i in range(len(data))])
data['dcmaxod'] = (data['open']-donchian_channel_max)/donchian_channel_max
data['dcminod'] = (data['open']-donchian_channel_min)/donchian_channel_min

num_all = data.shape[1]


#features owned only by previous data(include close,high,low,vol)
data['price_change'] = (data['close']-data['open']) /data['open']
data['vol_change'] = 0
data['vol_change'][1:] = (data['vol'][1:].values-data['vol'][:-1].values) /data['vol'][:-1].values
data['ibs'] = (data['close']-data['low']) /(data['high']-data['low'])

data['dcmaxcd'] = (data['close']-donchian_channel_max)/donchian_channel_max
data['dcmincd'] = (data['close']-donchian_channel_min)/donchian_channel_min

#data['macd'] = MACD(data).macd
#data['macdsignal'] = MACD(data).macdsignal
#data['macdhist'] = MACD(data).macdhist

data['%R'] = (np.array([max(data['high'][max(i,14)-14:max(i,14)]) for i in range(len(data))])-data.close.values)/((np.array([max(data['high'][max(i,14)-14:max(i,14)]) for i in range(len(data))])-np.array([min(data['low'][max(i,14)-14:max(i,14)]) for i in range(len(data))])))#Williams %R is a momentum indicator The default setting for Williams %R is 14 periods, which can be days, weeks, months or an intraday timeframe. 

#
y = [1 if data['close'][i]>data['open'][i] else 0 for i in range(len(data))]
y = y[N-1:]

n_windows = data.shape[0]-N+1
windows = range(n_windows)

#%% features of open,high,low,close,vol
d = np.array(data.ix[:,:5])
d = np.array([d[w:w+N].ravel() for w in windows])

#generated features for all days that can be used in training
d_na = np.array(data.ix[:,5:num_all])
d_na = np.array([d_na[w:w+N].ravel() for w in windows])

d_n = np.array(data.ix[:,num_all:])
d_n = np.array([d_n[w:w+N-1].ravel() for w in windows])

nday = 1500

d = d[len(data)- nday:]
d_na = d_na[len(data)- nday:]
d_n = d_n[len(data)- nday:]
y = np.array(y[len(data)- nday:])

#%%

def normalizeNday(stocks,N):
    def process_column(i):
        #Replaces all high/low/vol data with 0, and divides all stock data by the opening price on the first day
        if operator.mod(i, 5) == 1:
            return stocks[i] * 0
        if operator.mod(i, 5) == 2:
            return stocks[i] * 0
        return stocks[i] * 0 if operator.mod(i, 5) == 4 else stocks[i] / stocks[0]

    #n = stocks.shape[0]
    stocks_dat =  np.array([ process_column(i) for i in range(N*5-4)]).transpose()
    #stocks_movingavgO9O10 = np.array([int(i > j) for i,j in zip(stocks_dat[:,45], stocks_dat[:,40])]).reshape((n, 1))
    #stocks_movingavgC9O10 = np.array([int(i > j) for i,j in zip(stocks_dat[:,45], stocks_dat[:,43])]).reshape((n, 1))
    #return np.hstack((stocks_dat, stocks_movingavgO9O10, stocks_movingavgC9O10))
    return stocks_dat
#%%
d_normalized = pd.DataFrame(np.hstack((np.array([normalizeNday(w,N) for w in d]),d_n,d_na)))

#remove constants
nunique = pd.Series([len(d_normalized[col].unique()) for col in d_normalized.columns], index = d_normalized.columns)
constants = nunique[nunique<2].index.tolist()    
for col in constants:
    del d_normalized[col]
d_normalized = np.array(d_normalized)

train = d_normalized[:int(len(d)*2/3.)]
train_y = y[:int(len(d)*2/3.)]
test = d_normalized[int(len(d)*2/3.):]
test_y = y[int(len(d)*2/3.):]

plt.scatter(d[:, (N-1)*5] / d[:, (N-1)*5-2],  d[:, (N-1)*5+3] / d[:, (N-1)*5])
plt.xlim((.8,1.2)); plt.ylim((.8,1.2))
plt.xlabel("Opening N / Closing N-1"); plt.ylabel("Closing N / Opening N-1")
plt.title("Correlation between interday and intraday stock movement")
plt.show()


#%%
print "preparing models"

modelname = "ridge"

if modelname == "ridge": 
    C = np.linspace(80, 130, num = 5)[::-1]
    models = [lm.LogisticRegression(penalty = "l2", C = c) for c in C]

if modelname == "lasso": 
    C = np.linspace(300, 2000, num = 5)[::-1]
    models = [lm.LogisticRegression(penalty = "l1", C = c) for c in C]

if modelname == "sgd": 
    C = np.linspace(0.00005, .01, num = 5)
    models = [lm.SGDClassifier(loss = "log", penalty = "l2", alpha = c, warm_start = False) for c in C]
    
if modelname == "randomforest":
    C = np.linspace(500, 5000, num = 5)
    models = [RandomForestClassifier(n_estimators = int(c)) for c in C]
    
if modelname == "gbt":
    C = np.linspace(10, 200, num = 10)
    models = [GradientBoostingClassifier(n_estimators = int(c)) for c in C]

#if modelname == 'svm':
#    print 

print "calculating cv scores"
cv_scores = [0] * len(models)
for i, model in enumerate(models):
    # for all of the models, save the cross-validation scores into the array cv_scores. ['accuracy', 'adjusted_rand_score', 'average_precision', 'f1', 'log_loss', 'mean_absolute_error', 'mean_squared_error', 'precision', 'r2', 'recall', 'roc_auc']
    cv_scores[i] = np.mean(cross_validation.cross_val_score(model, train, train_y, cv=5, scoring='accuracy'))
    #cv_scores[i] = np.mean(cross_validation.cross_val_score(model, X, y, cv=5, score_func = auc))
    print " (%d/%d) C = %f: CV = %f" % (i + 1, len(C), C[i], cv_scores[i])

# find which model and C is the best
best = cv_scores.index(max(cv_scores))
best_model = models[best]
best_cv = cv_scores[best]
best_C = C[best]

print "BEST %f: %f" % (best_C, best_cv)
#%%
print "training on full data with one algorithm"
# fit the best model on the full data
best_model.fit(train, train_y)

print "prediction with one algorithm"
# do a prediction and save it
pred = best_model.predict_proba(test)[:,1]
preds=(pred>0.5)+0
print accuracy_score(test_y,preds)#roc_auc_score(test_y,pred),f1_score(test_y,preds),precision_score(test_y,preds),recall_score(test_y,preds)



#%%stack
# The below model is the blend of our models
models = [lm.LogisticRegression(penalty='l2', C = 5000),
          lm.LogisticRegression(penalty='l1', C = 500),
#          RandomForestClassifier(n_estimators = 100),
#          GradientBoostingClassifier(n_estimators = 200),
          ]
#models = [lm.LogisticRegression(penalty='l2', C = 5000),
#          RandomForestClassifier(n_estimators = 100)
#          ]

"""
Function
--------
coded by wzchen
This function gives a matrix of predictors 
(predicted probability that the stock will go up from each of the models)
and a matrix of responses (did the stock go up or down) that will be used
as input in the logistic regression blender.

Parameters
----------
models : list
         list of models that we want to stack
X      : (N_stocks, N_predictors) matrix
         matrix of predictors that are input into the above list of models
y      : (N_stocks, 1) matrix
         matrix of responses that the list of models are trained on
folds  : int
         folds used in the same way as cross-validation. We break up the 
         data into this many equally-sized chunks, and then for each chunk,
         we use the rest of the chunks to make predictions about it

Returns
-------
new_X : (N_stocks, N_models)
        New predictor matrix, where the predictors for each stock are the 
        out of sample predicted probabilities of stock inrease from 
        each of the models in the list of models
new_Y : same contents as y, but will be reordered due to the process for how
        the new_X is calculated

"""

def get_oos_predictions(models, X, y, folds = 10):
    
    # this is simply so we know how far the model has progressed
    sys.stdout.write('.')
    predictions = [[] for _ in models]
    new_Y = []

    # for every fold of the data...
    for i in range(folds):

        # find the indices that we want to train and predict
        indxs = np.arange(i, X.shape[0], folds)
        indxs_to_fit = list(set(range(X.shape[0])) - set(np.arange(i, X.shape[0], folds)))

        # put together the predictions for each model
        for i, model in enumerate(models):
            predictions[i].extend(list(model.fit(X[indxs_to_fit,:], y[indxs_to_fit]).predict_proba(X[indxs,:])[:,1]))

        # put together the reordered new_Y
        new_Y = new_Y + list(y[indxs])

    # format everything for return
    new_X = np.hstack([np.array(prediction).reshape(len(prediction), 1) for prediction in predictions])
    new_Y = np.array(new_Y).reshape(len(new_Y), 1)
    return new_X, new_Y

# run the code and get the new_X and new_Y estimates.
new_train, new_Y = get_oos_predictions(models, train, train_y)

#%%
model_stacker = lm.LogisticRegression()
print np.mean(cross_validation.cross_val_score(model_stacker, new_train, new_Y.reshape(new_Y.shape[0]), cv=5, scoring = 'accuracy'))

model_stacker.fit(new_train, new_Y.reshape(new_Y.shape[0]))

print "prediction with stack models"

#generate new test data
predictions = [[] for model in models]
for i, model in enumerate(models):
            predictions[i].extend(list(model.fit(train, train_y).predict_proba(test)[:,1]))
new_test = np.hstack([np.array(prediction).reshape(len(prediction), 1) for prediction in predictions])

pred = model_stacker.predict_proba(new_test)[:,1]
#testfile = p.read_csv('./test.csv', sep=",", na_values=['?'], index_col=[0,1])

#ytest= np.array(p.read_table('./result.csv', sep = ","))
preds=(pred>0.5)+0
print accuracy_score(test_y,preds)#roc_auc_score(test_y,pred),f1_score(test_y,preds),precision_score(test_y,preds),recall_score(test_y,preds)


#%% backtesting-待完善

## Define algorithm
#def initialize(context):
#    pass
#
#def handle_data(context, data):
#    order(symbol('AAPL'), 10)
#    record(AAPL=data[symbol('AAPL')].price)
#
## Create algorithm object passing in initialize and
## handle_data functions
#algo_obj = TradingAlgorithm(initialize=initialize, 
#                            handle_data=handle_data)
#
## Run algorithm
#perf_manual = algo_obj.run(data)



#%%result display
#Converting data from zipline to pyfolio
#returns, positions, transactions, gross_lev = pf.utils.extract_rets_pos_txn_from_zipline(backtest)

a=data.price_change[:100]
pf.create_returns_tear_sheet(a,benchmark_rets=a)
#pf.create_full_tear_sheet(returns,
#                          positions=positions,
#                          transactions=transactions,
#                          gross_lev=gross_lev)