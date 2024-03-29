'''
PSNR methods check

author : obanmarcos
'''

import wandb
import torch
import os
import os, sys
from config import * 

sys.path.append(where_am_i())

import pytorch_lightning as pl
import argparse
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from utilities import dataloading_utilities as dlutils
from utilities.folders import *

from torchvision import transforms as T
from pytorch_msssim import SSIM
from torchmetrics import MultiScaleStructuralSimilarityIndexMeasure as MSSSIM
from models.models_system import MoDLReconstructor
from pathlib import Path
from training import train_utilities as trutils

from skimage.metrics import structural_similarity as ssim 
from skimage.metrics import peak_signal_noise_ratio as psnr_skimage
from cv2 import PSNR as psnr_cv2
from matplotlib.patches import Rectangle

use_default_model_dict = True
use_default_dataloader_dict = True
use_default_trainer_dict = True
acceleration_factor = 26

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

if use_default_model_dict == True:
    # ResNet dictionary parameters
    resnet_options_dict = {'number_layers': 8,
                        'kernel_size':3,
                        'features':64,
                        'in_channels':1,
                        'out_channels':1,
                        'stride':1, 
                        'use_batch_norm': False,
                        'init_method': 'xavier'}

    # Model parameters
    modl_dict = {'use_torch_radon': False,
                'metric': 'psnr',
                'number_layers': 8,
                'K_iterations' : 8,
                'number_projections_total' : 720,
                'acceleration_factor': acceleration_factor,
                'image_size': 100,
                'lambda': 0.05,
                'use_shared_weights': True,
                'denoiser_method': 'resnet',
                'resnet_options': resnet_options_dict,
                'in_channels': 1,
                'out_channels': 1}
    
    admm_dictionary = {'number_projections': modl_dict['number_projections_total'],
                    'alpha': 0.005, 
                    'delta': 2, 
                    'max_iter': 10, 
                    'tol': 10e-7, 
                    'use_invert': 0,
                    'use_warm_init' : 1,
                    'verbose': True}

    twist_dictionary = {'number_projections': modl_dict['number_projections_total'], 
                        'lambda': 1e-4, 
                        'tolerance':1e-4,
                        'stop_criterion':1, 
                        'verbose':1,
                        'initialization':0,
                        'max_iter':10000, 
                        'gpu':0,
                        'tau': 0.02}
    
    unet_dict = {'n_channels': 1,
                     'n_classes':1,
                     'bilinear': True,
                     'batch_norm': False,
                     'batch_norm_inconv': False,
                     'residual': False,
                     'up_conv': False}
     
    # Training parameters
    loss_dict = {'loss_name': 'psnr',
                'psnr_loss': torch.nn.MSELoss(reduction = 'mean'),
                'ssim_loss': SSIM(data_range=1, size_average=True, channel=1),
                'msssim_loss': MSSSIM(kernel_size = 1)}

    # Optimizer parameters
    optimizer_dict = {'optimizer_name': 'Adam+Tanh',
                    'lr': 1e-4}

    # System parameters
    model_system_dict = {'acc_factor_data':1,
                        'use_normalize': False,
                        'optimizer_dict': optimizer_dict,
                        'kw_dictionary_modl': modl_dict,
                        'loss_dict': loss_dict, 
                        'method':'modl',                 
                        'track_train': True,
                        'track_val': True,
                        'track_test': True,
                        'max_epochs':40, 
                        'load_path': '',
                        'save_path': 'MoDL_FA{}'.format(1),
                        'tv_iters': 5,
                        'metrics_folder': where_am_i('metrics'),
                        'models_folder': where_am_i('models'),
                        'track_alternating_admm': True,
                        'admm_dictionary': admm_dictionary,
                        'track_alternating_twist': True,
                        'twist_dictionary': twist_dictionary,
                        'track_unet': True,
                        'unet_dictionary':unet_dict}

# PL Trainer and W&B logger dictionaries
if use_default_trainer_dict == True:


    logger_dict = {'project':'deepopt',
                    'entity': 'omarcos', 
                    'log_model': True}

    lightning_trainer_dict = {'max_epochs': 40,
                                'log_every_n_steps': 10,
                                'check_val_every_n_epoch': 1,
                                'gradient_clip_val' : 0.5,
                                'accelerator' : 'gpu', 
                                'devices' : 1,
                                'fast_dev_run' : False,
                                'default_root_dir': where_am_i('metrics')}

    profiler = None
    # profiler = SimpleProfiler(dirpath = './logs/', filename = 'Test_training_profile_pytorch')
    # profiler = PyTorchProfiler(dirpath = './logs/', filename = 'Test_training_profile_pytorch')

    trainer_dict = {'lightning_trainer_dict': lightning_trainer_dict,
                    'use_k_folding': True, 
                    'track_checkpoints': False,
                    'epoch_number_checkpoint': 10,
                    'use_swa' : False,
                    'use_accumulate_batches': False,
                    'k_fold_number_datasets': 3,
                    'use_logger' : False,
                    'resume':'allow',
                    'logger_dict': logger_dict,
                    'track_default_checkpoints'  : False,
                    'use_auto_lr_find': False,
                    'batch_accumulate_number': 3,
                    'use_mixed_precision': False,
                    'batch_accumulation_start_epoch': 0, 
                    'profiler': profiler,
                    'restore_fold': False,
                    'fold_number_restore': 2,
                    'acc_factor_restore': 22}

# Dataloader dictionary
if use_default_dataloader_dict == True:
    
    # data_transform = T.Compose([T.ToTensor()])
    data_transform = None                                    
    
    dataloader_dict = {'datasets_folder': where_am_i('datasets'),
                        'number_volumes' : 0,
                        'experiment_name': 'Bassi',
                        'img_resize': 100,
                        'load_shifts': True,
                        'save_shifts':False,
                        'number_projections_total': 720,
                        'acceleration_factor':acceleration_factor,
                        'train_factor' : 0.8, 
                        'val_factor' : 0.2,
                        'test_factor' : 0.2, 
                        'batch_size' : 8, 
                        'sampling_method' : 'equispaced-linear',
                        'shuffle_data' : True,
                        'data_transform' : data_transform,
                        'num_workers' : 8,
                        'use_subset_by_part' :False}

artifact_names_psnr = ['model-3dp1wex6:v0']

dataset_list = ['/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140114_5dpf_lower tail_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140315_1dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140114_5dpf_body_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140114_5dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140315_3dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140117_3dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140519_5dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140117_3dpf_lower tail_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140114_5dpf_upper tail_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140714_5dpf_head_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140117_3dpf_body_26', '/home/obanmarcos/Balseiro/DeepOPT/datasets/x26/140117_3dpf_upper tail_26']

def normalize_01(img):

    return (img-img.min())/(img.max()-img.min())


def psnr_per_box(target, rec, box):

    target_region = target[box[0,0]:box[0,1],box[1,0]:box[1,1]]
    rec_region = rec[box[0,0]:box[0,1],box[1,0]:box[1,1]] 

    target_region = (target_region-target_region.mean())/target_region.std()
    rec_region = (rec_region-rec_region.mean())/rec_region.std()
    im_range = target_region.max()-target_region.min()

    return round(psnr_skimage(target_region, rec_region, data_range = im_range), 2)

def mean_box(image, c, w, h):
    
    image = image[c[0]:c[0]+w, c[1]:c[1]+h]
    image = (image-image.mean())/image.std()
    
    return np.round(np.mean(image), 2)

def box_list(c, h, w):

    return np.array([[c[0], c[0]+w], [c[1], c[1]+h]])


if __name__ == '__main__':
    
    part = dataset_list[-3].split('_')[-2] 
    artifact_names = artifact_names_psnr
    testing_name_group = 'x{}_test-PSNR'.format(acceleration_factor)

    run_name = 'test_metrics_kfold_x{}'.format(acceleration_factor)
    metric = 'psnr'

    user_project_name = 'omarcos/deepopt/'

    trainer_system = trutils.TrainerSystem(trainer_dict, dataloader_dict, model_system_dict)
    trainer_system.set_datasets_list(dataset_list)
    
    train_dataloader, val_dataloader, test_dataloader = trainer_system.generate_K_folding_dataloader()

    artifact_dir = '/home/obanmarcos/Balseiro/DeepOPT/artifacts/model-2jnmr8t0:v0'
    
    model = MoDLReconstructor.load_from_checkpoint(Path(artifact_dir) / "model.ckpt", kw_dictionary_model_system = model_system_dict) 

    idx = 7
    batch_idx = 60

    for i, batch in enumerate(test_dataloader):
        
        unfiltered_us_rec, filtered_us_rec, filtered_fs_rec = batch
        
        if i == batch_idx:
            break
    
    unfiltered_us_rec_image = normalize_01(unfiltered_us_rec[idx,0,...].cpu().numpy())
    filtered_us_rec_image = normalize_01(filtered_us_rec[idx,0,...].cpu().numpy())
    filtered_fs_rec_image = normalize_01(filtered_fs_rec[idx,0,...].cpu().numpy())
    modl_reconstructed = normalize_01(model(unfiltered_us_rec.to(device))['dc'+str(model.model.K)][idx,0,...].detach().cpu().numpy())

    alt_input = (unfiltered_us_rec[idx,0,...].cpu().numpy().T - unfiltered_us_rec[idx,0,...].cpu().numpy().T.mean())/unfiltered_us_rec[idx,0,...].cpu().numpy().T.std()
    alt_true = (filtered_fs_rec[idx,0,...].cpu().numpy().T - filtered_fs_rec[idx,0,...].cpu().numpy().T.mean())/filtered_fs_rec[idx,0,...].cpu().numpy().T.std()
    
    
    images = [filtered_fs_rec_image, unfiltered_us_rec_image, filtered_us_rec_image,  modl_reconstructed]

    # Boxes
    c_green = [0, 0]
    h_green, w_green = (20, 20)
    c_red = [40, 40]
    h_red, w_red = (50, 50)

    box_green = box_list(c_green, w_green, h_green)
    box_red = box_list(c_red, w_red, h_red)

    boxes = [box_green, box_red]

    titles = ['Filtered backprojection - \nFully Sampled\n',
              'Unfiltered backprojection - \nUndersampled\n', 
              'Filtered backprojection - \nUndersampled X22\n',
              'MoDL reconstruction\n']

    metrics = ['']+[
               'SSIM: {}\n PSNR (Box Green): {} dB\n PSNR (Box Red): {} dB'.format(round(ssim(images[0], image), 2), psnr_per_box(images[0], image, box_green), psnr_per_box(images[0], image, box_red)) for image in images[1:]]

    fig, axs = plt.subplots(2, len(images)//2, figsize = (12,10))
    axs = axs.flatten()
    
    for (ax, image, title, metric) in zip(axs, images, titles, metrics):

        rect_green = Rectangle(c_green, w_green, h_green, linewidth=1, edgecolor='r', facecolor='none')
        rect_red = Rectangle(c_red, w_red, h_red, linewidth=1, edgecolor='g', facecolor='none')
        
        ax.imshow(image)
        ax.set_title(title+metric)
        ax.set_axis_off()
        ax.add_patch(rect_green)
        ax.add_patch(rect_red)

        # Mean value - Green
        ax.text(c_green[0], c_green[1]+h_green//2, s = 'Mean: {:0.4f}'.format(mean_box(image, c_green, w_green, h_green)), c = 'white', fontsize=12)

        # Mean value - Red
        ax.text(c_red[0], c_red[1]+h_red//2, s = 'Mean: {:0.4f}'.format(mean_box(image, c_red, w_red, h_red)), c = 'white', fontsize=12)

    fig.savefig('./logs/TestPSNR_PSNR-11_PerPatch-{}.pdf'.format(part), bbox_inches = 'tight')

