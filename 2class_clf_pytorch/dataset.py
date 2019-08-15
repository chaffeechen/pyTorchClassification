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

# image_size = 256

class TrainDataset(Dataset):
    def __init__(self, root: Path, df: pd.DataFrame, debug: bool = True, name: str = 'train', imgsize = 256):
        super().__init__()
        self._root = root
        self._df = df
        self._debug = debug
        self._name = name
        self._imgsize = imgsize

    def __len__(self):
        return len(self._df)

    def __getitem__(self, idx: int):
        item = self._df.iloc[idx]
        image = load_transform_image(item, self._root, imgsize = self._imgsize,debug=self._debug, name=self._name)
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


# #item \
# # - attribute_ids - id - folds - data: a,b
class TrainDatasetSelected(Dataset):
    def __init__(self, root: Path, df: pd.DataFrame, debug: bool = True, name: str = 'train', imgsize = 256):
        super().__init__()
        self._root = root
        self._df = df
        self._debug = debug
        self._name = name
        self._imgsize = imgsize
        self._dfA = df[df['data']=='a']
        self._dfB = df[df['data']=='b']

    def __len__(self):
        return len(self._df)

    def __getitem__(self, idx: int):
        #choose label from data a
        #choose any tow sample from data b bcz 1 image per class
        labelA = int(idx % 128)
        #https://stackoverflow.com/questions/21415661/logical-operators-for-boolean-indexing-in-pandas
        # dfA = self._df[(self._df['data'] == 'a')&(self._df['attribute_ids'] == str(labelA))]
        dfA = self._dfA[self._dfA['attribute_ids'] == str(labelA)]
        len_dfA = len(dfA)
        pair_idxA = [random.randint(0, len_dfA) for _ in range(2)]

        imagesA = []
        imagesB = []
        single_targetsA = []
        single_targetsB = []

        for idxA in pair_idxA:
            item = dfA.iloc[idxA]
            image = load_transform_image(item, self._root, imgsize=self._imgsize, debug=self._debug, name=self._name)
            lb = int(item.attribute_ids) - 1
            assert(lb < N_CLASSES)
            imagesA.append(image)
            single_targetsA.append(lb)

        dfB = self._dfB
        len_dfB = len(dfB)
        pair_idxB = [random.randint(0, len_dfB) for _ in range(2)]

        for idxB in pair_idxB:
            item = dfB.iloc[idxB]
            image = load_transform_image(item, self._root, imgsize=self._imgsize, debug=self._debug, name=self._name)
            imagesB.append(image)
            lb = int(item.attribute_ids) - 1
            single_targetsB.append(lb)

        return (imagesA,imagesB), (single_targetsA,single_targetsB)


def collate_TrainDatasetSelected(batch):
    """
    special collate_fn function for UDF class TrainDatasetSelected
    :param batch: 
    :return: 
    """
    # batch_size = len(batch)
    imagesA = []
    imagesB = []
    labelsA = []
    labelsB = []

    for b in batch:
        if b[0] is None:
            continue
        else:
            imagesA.extend(b[0][0])
            imagesB.extend(b[0][1])
            labelsA.extend(b[1][0])
            labelsB.extend(b[1][1])

    imagesA.extend(imagesB)
    labelsA.extend(labelsB)

    imagesA = torch.stack(imagesA,0) #images : list of [C,H,W] -> [Len_of_list, C, H,W]
    labelsA = torch.from_numpy(np.array(labelsA))
    return imagesA,labelsA


class TTADataset:
    def __init__(self, root: Path, df: pd.DataFrame, tta_code , imgsize = 256):
        self._root = root
        self._df = df
        self._tta_code = tta_code
        self._imgsize = imgsize

    def __len__(self):
        return len(self._df)

    def __getitem__(self, idx):
        item = self._df.iloc[idx % len(self._df)]
        image = load_test_image(item, self._root, self._tta_code, self._imgsize)
        return image, item.id
    
    
def load_transform_image(item, root: Path, imgsize=256,debug: bool = False, name: str = 'train'):
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

    image = cv2.resize(image ,(imgsize, imgsize))

    if debug:
        image.save('_debug.png')

    image = np.transpose(image, (2, 0, 1))
    image = image.astype(np.float32)
    image = image.reshape([-1, imgsize, imgsize])
    image = image / 255.0

    # is_venn = True
    # if is_venn:
    #     # mean = [0.485, 0.456, 0.406]
    #     # std = [0.229, 0.224, 0.225]
    #     image[0,:,:] = (image[0,:,:] - 0.485) / 0.229
    #     image[1,:,:] = (image[1,:,:] - 0.456) / 0.224
    #     image[2,:,:] = (image[2,:,:] - 0.406) / 0.225

    return torch.FloatTensor(image)

def load_test_image(item, root: Path, tta_code, imgsize):
    image = load_image(item, root)
    image = aug_image(image, augment = tta_code)
    image = cv2.resize(image ,(imgsize, imgsize))

    image = np.transpose(image, (2, 0, 1))
    image = image.astype(np.float32)
    image = image.reshape([-1, imgsize, imgsize])
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

