import torch
import torch.utils.data
import torchvision
import numpy as np


class ImbalancedDatasetSampler(torch.utils.data.sampler.Sampler):
    """Samples elements randomly from a given list of indices for imbalanced dataset
    Arguments:
        indices (list, optional): a list of indices
        num_samples (int, optional): number of samples to draw
        callback_get_label func: a callback-like function which takes two arguments - dataset and index
    """

    def __init__(self, dataset, indices=None, num_samples=None, callback_get_label=True):

        # if indices is not provided,
        # all elements in the dataset will be considered

        # the number of images
        self.dataset = dataset
        self.indices = list(range(len(dataset))) \
            if indices is None else indices

        # define custom callback
        self.callback_get_label = callback_get_label

        # if num_samples is not provided,
        # draw `len(indices)` samples in each iteration
        self.num_samples = len(self.indices) \
            if num_samples is None else num_samples
        print('num_samples: ', self.num_samples)
        # distribution of classes in the dataset
        label_to_count = {}
        i = 0
        for idx in self.indices:
            i += 1
            if i % 1000 == 0:
                print('i: ', i)
            label = self._get_label(dataset, idx)
            if label in label_to_count:
                label_to_count[label] += 1
            else:
                label_to_count[label] = 1

        # {3: 49, 1: 150, 2: 150, 4: 150}
        # print(label_to_count)
        # weight for each sample
        weights = [1.0 / label_to_count[self._get_label(dataset, idx)]
                   for idx in self.indices]
        np.save('weight_20210115.npy', weights, allow_pickle=True)
        weights = np.load("weight_20210115.npy").tolist()
        self.weights = torch.DoubleTensor(weights)

    def _get_label(self, dataset, idx):
        if self.callback_get_label:
            # print(self.dataset.__getitem__(idx)[1], self.dataset.__getitem__(idx)[2])
            return self.dataset.__getitem__(idx)[1]
        elif isinstance(dataset, torchvision.datasets.MNIST):
            return dataset.train_labels[idx].item()
        elif isinstance(dataset, torchvision.datasets.ImageFolder):
            return dataset.imgs[idx][1]
        elif isinstance(dataset, torch.utils.data.Subset):
            return dataset.dataset.imgs[idx][1]
        else:
            raise NotImplementedError

    def __iter__(self):
        # return (self.indices[i] for i in torch.multinomial(self.weights, self.num_samples, replacement=True))
        return iter(torch.multinomial(self.weights, self.num_samples, replacement=True).tolist())

    def __len__(self):
        return self.num_samples

