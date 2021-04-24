import torch
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
from torch import nn
import torch.nn.functional as F
import torch.nn as nn
from tqdm import tqdm
import numpy as np
class RNN_1d(nn.Module):

    def __init__(self, 
                 n_output_channels = 1, 
                 filter_widths = [1, 1, 1, 1], 
                 num_chunks = 5, 
                 max_pool_factor = 4, 
                 nchannels = [32, 32, 32, 16, 16],
                 n_hidden = 32, 
                 dropout = 0.2):
        
        super(RNN_1d, self).__init__()
        self.rf = 0 # running estimate of the receptive field
        self.chunk_size = 1 # running estimate of num basepairs corresponding to one position after convolutions
        rnn_layers = []
        rnn_layers += [nn.RNN(input_size=5, hidden_size=32, num_layers=2,nonlinearity='relu', dropout=0.2, batch_first=True)]
        self.rnn_net = nn.Sequential(*rnn_layers)

        # rnn_layers2 = []
        # rnn_layers2 += [nn.RNN(input_size=32, hidden_size=16, num_layers=2,nonlinearity='relu', dropout=0.2, batch_first=True)]
        # self.rnn_net2 = nn.Sequential(*rnn_layers2)

        conv_layers = []
        for i in range(len(nchannels)-1):
            conv_layers += [ nn.Conv1d(nchannels[i], nchannels[i+1], filter_widths[i], padding = 0),
                        nn.BatchNorm1d(nchannels[i+1]), # tends to help give faster convergence: https://arxiv.org/abs/1502.03167
                        nn.Dropout2d(dropout), # popular form of regularization: https://jmlr.org/papers/v15/srivastava14a.html
                        nn.MaxPool1d(max_pool_factor), 
                        nn.ELU(inplace=True)  ] # popular alternative to ReLU: https://arxiv.org/abs/1511.07289
            assert(filter_widths[i] % 2 == 1) # assume this
            self.rf += (filter_widths[i] - 1) * self.chunk_size
            self.chunk_size *= max_pool_factor

        # If you have a model with lots of layers, you can create a list first and 
        # then use the * operator to expand the list into positional arguments, like this:
        self.conv_net = nn.Sequential(*conv_layers)

        self.seq_len = num_chunks * self.chunk_size + self.rf # amount of sequence context required

        print("Receptive field:", self.rf, "Chunk size:", self.chunk_size, "Number chunks:", num_chunks)

        self.dense_net = nn.Sequential( nn.Linear(nchannels[-1] * num_chunks, n_hidden),
                                        nn.Dropout(dropout),
                                        nn.ELU(inplace=True), 
                                        nn.Linear(n_hidden, n_output_channels) )

    def forward(self, x):
        x = x.permute(0,2,1)
        a,b = self.rnn_net(x)
        print(a.shape)
        # a,b = self.rnn_net2(a)
        a = a.permute(0,2,1)
        print(a.shape)
        
        #print(a.shape)#torch.Size([100, 32, 1])
        net = self.conv_net(a)
        net = net.view(net.size(0), -1)
        net = self.dense_net(net)
        return(net)