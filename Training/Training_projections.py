"""
Train the model with different projections angles
author: obanmarcos
"""
import os
import os,time, sys
os.chdir('/home/marcos/DeepOPT/')
sys.path.append('Utilities/')
sys.path.append('OPTmodl/')
import numpy as np
import random
import matplotlib.pyplot as plt
import pandas as pd
import DataLoading as DL
from Folders_cluster import *
import ModelUtilities as modutils
import torch
from torch_radon import Radon, RadonFanbeam
from skimage.transform import radon, iradon
import phantominator as ph
import torchvision
import model_torch as modl
import pickle
from tqdm import tqdm

# Using CPU or GPU
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
folder_paths = [ f140315_3dpf, f140419_5dpf, f140115_1dpf,f140714_5dpf] # Folders to be used

umbral_reg = 50
train_dataset, test_dataset = modutils.formRegDatasets(folder_paths, umbral_reg)

#%% Datasets 
# Training with more than one dataset
number_projections = [72]

train_size = 900
val_size = 100
test_size = 100

batch_size = 5
img_size = 100

train_infos = {}
test_loss_dict = {}

for proj_num in number_projections:
    
    # Load desired and undersampled datasets, on image space. Testing on Test Dataset
    dataloaders = modutils.formDataloaders(train_dataset, test_dataset, proj_num, train_size, val_size, test_size, batch_size, img_size)
    
    #%% Model Settings
    nLayer = 3
    K = 5
    epochs = 20
    lam = 0.05
    max_angle = 720
    
    model = modl.OPTmodl(nLayer, K, proj_num, img_size, None, lam)
    loss_fn = torch.nn.MSELoss(reduction = 'sum')
    loss_fbp_fn = torch.nn.MSELoss(reduction = 'sum') 
    lr = 1e-3
    optimizer = torch.optim.RMSprop(model.parameters())
    
    ### Training
    model, train_info = modutils.model_training(model, loss_fn, loss_fbp_fn, optimizer, dataloaders, device, results_folder, num_epochs = epochs, disp = True, do_checkpoint = 0)
     
    train_infos[proj_num] = train_info
    
    print('Test MODL loss {}'.format(train_infos[proj_num]['train'][-1]))
    print('Test FBP loss {}'.format(train_infos[proj_num]['train_fbp'][-1]))

    #%% save loss for fbp and modl network
    with open(results_folder+'FBP_error_projections_nlay{}_epochs{}_K{}_lam{}.pkl'.format(nLayer, epochs, K, lam), 'wb') as f:
    
        pickle.dump(train_infos, f)
        print('Diccionario salvado para proyección {}'.format(proj_num))
    
    modutils.save_net(model_folder+'K_{}_lam_{}_nlay_{}_proj_{}'.format(K, lam, nLayer, proj_num), model)
   
    ### Testing part
    test_loss_total = []
    test_loss_fbp_total = []

    for inp, target in tqdm(zip(dataloaders['test']['x'], dataloaders['test']['y'])): 
        
        pred = model(inp)
        loss_test = loss_fn(pred['dc'+str(K-1)], target)
        loss_test_fbp = loss_fbp_fn(inp, target)

        test_loss_total.append(modutils.psnr(img_size, loss_test.item()))
        test_loss_fbp_total.append(modutils.psnr(img_size, loss_test_fbp.item()))
    
    modutils.plot_outputs(target, pred, results_folder+'Test_images_proj{}.pdf'.format(proj_num))

    test_loss_dict[proj_num] = {'loss_net': test_loss_total, 'loss_fbp': test_loss_fbp_total}

    with open(results_folder+'Unique_Proj{}_nLay{}_K{}_lam{}.pkl'.format(proj_num, nLayer, K, lam), 'wb') as f:
        
        pickle.dump(test_loss_dict, f)
        print('Diccionario salvado para proyección {}'.format(proj_num))

    del model