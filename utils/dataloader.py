from math import ceil
import sklearn
import torch
# from torch.utils.data import Dataset, DataLoader

import torch.nn as nn
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

import pandas as pd

N_SENSORS = 180

class LiDARDataset(torch.utils.data.Dataset):
  '''
  Prepare the dataset for regression
  '''

  def __init__(self, 
               X:np.ndarray, y:np.ndarray, 
               x_mean:np.float, x_std:np.float,
               prev_steps:int=None,
               standarize:bool=False):
    
    if not torch.is_tensor(X) and not torch.is_tensor(y):
        if standarize:
            X = (X - x_mean)/x_std

    if prev_steps:
        X = prev_timesteps_feature_enginering(X, prev_steps)
    
    self.X = torch.Tensor(X[:,None]) # add channel dimension of size 1
    self.y = torch.Tensor(y[:,None])

  def __len__(self):

    return len(self.X)

  def __getitem__(self, i):
    return self.X[i], self.y[i]


def load_LiDARDataset(path_x:str, 
                      path_y:str, 
                      batch_size:int, 
                      mode:str=None, 
                      prev_steps:bool=None,
                      train_test_split:float=0.7, 
                      train_val_split:float=0.2, 
                      shuffle:bool=True):
    '''
    Load training set, validation set and test set from paths.
    '''
    X = np.loadtxt(path_x)
    X =  1 - X/150

    if mode is None:
        y = np.loadtxt(path_y)
    else:
        y = calculate_total_risk(path_y, mode)
    
    data_size  = len(X)
    train_size = int(train_test_split * data_size)
    val_size   = int(train_val_split * train_size)
    test_size  = data_size - train_size
    train_size = train_size - val_size
    
    # Training set
    X_train = X[:train_size,:]
    y_train = y[:train_size]
    
    x_mean, x_std = X_train.mean(), X_train.std() # Mean and std only from training set
    
    data_train = LiDARDataset(X_train, y_train, x_mean, x_std, prev_steps=prev_steps)
    dataloader_train = torch.utils.data.DataLoader(data_train, 
                                                batch_size=batch_size, 
                                                shuffle=shuffle, 
                                                num_workers=1,
                                                drop_last=True)

    # Validation set
    X_val = X[train_size:train_size+val_size,:]
    y_val = y[train_size:train_size+val_size]
    data_val = LiDARDataset(X_val, y_val, x_mean, x_std, prev_steps=prev_steps)
    dataloader_val = torch.utils.data.DataLoader(data_val, 
                                                 batch_size=batch_size, 
                                                 shuffle=shuffle, 
                                                 num_workers=1,
                                                 drop_last=True)
    # Test set
    X_test = X[-test_size:,:]
    y_test = y[-test_size:]
    data_test = LiDARDataset(X_test, y_test, x_mean, x_std, prev_steps=prev_steps)  
    dataloader_test = torch.utils.data.DataLoader(data_test,
                                                  batch_size=1, 
                                                  shuffle=shuffle, 
                                                  num_workers=1,
                                                  drop_last=True)

    return data_train, data_val, data_test, dataloader_train, dataloader_val, dataloader_test


def calculate_total_risk(path_y:str, mode:str) -> np.ndarray:
    # Y has a list of CRI at each row -> number of risks varies at each row -> read with predefined number of cols -> pandas
    # Placeholder, can consider more sophisticated ways to calculate the total risk when more then one obstacle are present.

    Y = pd.read_csv(path_y, delimiter=r"\s+", header=None, names=[i for i in range(8)]) # assume a maximum number of 5 obstacles at a time

    if mode=='sum':
        y = Y.sum(axis=1)
 
    elif mode == 'max':
        y = Y.max(axis=1)

    else:
        y = np.mean(Y, axis=1)

    y = y.to_numpy(copy=True)
    return y


def prev_timesteps_feature_enginering(X:np.ndarray, time_steps:int):

    X_concat = X[:,:,None].copy()
    X_prev   = X.copy()
    x_empty  = np.array([150]*N_SENSORS).reshape((1, N_SENSORS))

    for i in range(time_steps):
        X_prev = X_prev[:-1,:].copy()
        X_prev = np.concatenate((x_empty, X_prev), axis=0)
        X_concat = np.concatenate((X_concat, X_prev[:,:,None]), axis=2)
    
    return X_concat
    
