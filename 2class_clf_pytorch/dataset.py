from pathlib import Path
from typing import Callable, List
import random
import cv2
import pandas as pd
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision.transforms import (
    ToTensor, Normalize, Compose, Resize, CenterCrop, RandomCrop,
    RandomHorizontalFlip)
from transforms import tensor_transform
from aug import *

N_CLASSES = 128
DATA_ROOT = '/home/ubuntu/CV/data/furniture'
# DATA_ROOT = '/home/ubuntu/CV/data/wework_activity/Classification/multi_data'

image_size = 256

class TrainDataset(Dataset):
    def __init__(self, root: Path, df: pd.DataFrame, debug: bool = True, name: str = 'train'):
        super().__init__()
        self._root = root
        self._df = df
        self._debug = debug
        self._name = name

    def __len__(self):
        return len(self._df)

    def __getitem__(self, idx: int):
        item = self._df.iloc[idx]
        image = load_transform_image(item, self._root, debug=self._debug, name=self._name)
        # target = torch.zeros(N_CLASSES)
        lb = item.attribute_ids
        # print(lb)

        # for cls in range(N_CLASSES):
        #     target[cls] = int(lb[cls + 1])
        # clsval = int(lb[5])
        # target = torch.from_numpy(np.array(item.attribute_ids))
        clsval = int(lb)-1
        target = torch.from_numpy(np.array(clsval))
        return image, target


class TTADataset:
    def __init__(self, root: Path, df: pd.DataFrame, tta_code):
        self._root = root
        self._df = df
        self._tta_code = tta_code

    def __len__(self):
        return len(self._df)

    def __getitem__(self, idx):
        item = self._df.iloc[idx % len(self._df)]
        image = load_test_image(item, self._root, self._tta_code)
        return image, item.id
    
    
def load_transform_image(item, root: Path, debug: bool = False, name: str = 'train'):
    image = load_image(item, root)

    if name == 'train':
        # alpha = random.uniform(0, 0.2)
        # image = do_brightness_shift(image, alpha=alpha)
        image = random_flip(image, p=0.5)
        # angle = random.uniform(0, 1)*360
        # image = rotate(image, angle, center=None, scale=1.0)
        ratio = random.uniform(0.7, 0.99)
        image = random_cropping(image, ratio = 0.8, is_random = True)
        #image = random_erasing(image, probability=0.5, sl=0.02, sh=0.4, r1=0.3)
    else:
        image = random_cropping(image, ratio=0.8, is_random=False)

    image = cv2.resize(image ,(image_size, image_size))

    if debug:
        image.save('_debug.png')

    image = np.transpose(image, (2, 0, 1))
    image = image.astype(np.float32)
    image = image.reshape([-1, image_size, image_size])
    image = image / 255.0

    # is_venn = True
    # if is_venn:
    #     # mean = [0.485, 0.456, 0.406]
    #     # std = [0.229, 0.224, 0.225]
    #     image[0,:,:] = (image[0,:,:] - 0.485) / 0.229
    #     image[1,:,:] = (image[1,:,:] - 0.456) / 0.224
    #     image[2,:,:] = (image[2,:,:] - 0.406) / 0.225

    return torch.FloatTensor(image)

def load_test_image(item, root: Path, tta_code):
    image = load_image(item, root)
    image = aug_image(image, augment = tta_code)
    image = cv2.resize(image ,(image_size, image_size))

    image = np.transpose(image, (2, 0, 1))
    image = image.astype(np.float32)
    image = image.reshape([-1, image_size, image_size])
    image = image / 255.0

    # is_venn = True
    # if is_venn:
    #     # mean = [0.485, 0.456, 0.406]
    #     # std = [0.229, 0.224, 0.225]
    #     image[0,:,:] = (image[0,:,:] - 0.485) / 0.229
    #     image[1,:,:] = (image[1,:,:] - 0.456) / 0.224
    #     image[2,:,:] = (image[2,:,:] - 0.406) / 0.225

    return torch.FloatTensor(image)

def load_image(item, root: Path) -> Image.Image:
    # print(str(root + '/' + f'{item.id}.jpg'))
    image = cv2.imread(str(root + '/' + f'{item.id}'))
    # print(image.shape)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image

# image name looks like : idx_copy.jpg
def get_ids(root: Path) -> List[str]:
    return sorted({p.name.split('_')[0] for p in root.glob('*.jpg')})

