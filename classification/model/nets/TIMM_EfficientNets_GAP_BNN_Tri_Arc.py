import torch
import torch.nn as nn
import os
from copy import deepcopy
from torch.utils.tensorboard import SummaryWriter
import torchvision.models as models

from ..components import build_backbone
from ..components import build_layer
from ..components import build_aggregation
from ..components import build_head
from ..layers.rga import *
from ...model import losses as losses
from ...utils.utils import *


class TIMM_EfficientNet_B4_GAP_BNN_Tri_Arc(nn.Module):
    def __init__(self, cfg):
        super(TIMM_EfficientNet_B4_GAP_BNN_Tri_Arc, self).__init__()
        self.cfg = cfg
        cfg_model = self.cfg['model']
        cfg_model = deepcopy(cfg_model)

        # get configuration
        cfg_backbone = cfg_model['backbone']
        cfg_aggregation = cfg_model['aggregation']
        cfg_head = cfg_model['heads']
        cfg_losses = cfg_model['losses']

        # log
        log_dir = cfg['log_dir']
        self.write = SummaryWriter(log_dir=log_dir)
        self.step = 0

        # net
        self.backbone = build_backbone(cfg_backbone)
        self.aggregation = build_aggregation(cfg_aggregation)
        self.head = build_head(cfg_head)

        # Arcface loss
        cfg_ce = cfg_losses[0]
        loss_type = cfg_ce.pop("type")
        self.celoss = getattr(losses, loss_type)(**cfg_ce)

        # Triplet Loss
        cfg_triplet = cfg_losses[1]
        loss_type = cfg_triplet.pop("type")
        assert loss_type == "TripletLoss"
        self.tripletloss = getattr(losses, "TripletLoss")(**cfg_triplet)

    def forward(self, inputs, targets=None, extract_features_flag=False, features_type="after", ya=None, yb=None, lam_a=None, lam_b=None, reback=None):
        assert features_type in ("backbone", "before", "after", "both")

        b_features = self.backbone(inputs)

        if extract_features_flag and (features_type == 'backbone'):
            # [N, C, H, W]
            return b_features

        features = self.aggregation(b_features)

        # 从 Head 之前抽取特征
        if extract_features_flag and (features_type == 'before'):
            # [N, C, 1, 1] -> [N, C]
            return features[..., 0, 0]

        head_features = self.head(features)

        # 从 Head 之后抽取
        if extract_features_flag and (features_type == 'after'):
            # [N, C]
            return head_features

        # both
        if extract_features_flag and (features_type == 'both'):
            return features[..., 0, 0], head_features

        # if self.training:
        #     # 获得 loss
        #     ce_value = self.celoss(head_features, ya, yb, lam_a, lam_b)
        #     # print('ce loss: ', ce_value.cpu().data.numpy())
        #     total_loss = torch.unsqueeze(ce_value, 0)
        #     # print('total_loss: ', total_loss)
        #     return total_loss

        # 训练阶段
        if self.training:
            # for Triplet Loss
            # aggregation 处提取特征
            triplet_value = self.tripletloss(features[..., 0, 0], targets.long())

            # for ArcFace loss
            ce_value = self.celoss(head_features, targets.long())
            # print('ce loss: ', ce_value.cpu().data.numpy())

            self.write.add_scalar("Triplet Loss", triplet_value.cpu().data.numpy())
            self.write.add_scalar("CE Loss", ce_value.cpu().data.numpy())

            total_loss = torch.unsqueeze(triplet_value, 0) + torch.unsqueeze(ce_value, 0)
            # print('tripletloss: {:.4}, celoss: {:.4f}, total_loss: {:.4f}'.format(triplet_value, ce_value, total_loss.data.item()))
            return total_loss
        else:
            # 获得 fc 的输出
            # loss_dict = {}
            # pred_logit = self.celoss(head_features, targets.long())
            # loss_dict['logit'] = pred_logit
            # return loss_dict
            pred_logit = self.celoss(head_features, targets.long())
            return pred_logit
