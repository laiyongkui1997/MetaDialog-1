#!/usr/bin/env python
import torch
from torch import nn
from typing import Tuple, List
from models.modules.context_embedder_base import ContextEmbedderBase
from models.modules.emission_scorer_base import EmissionScorerBase


class FewShotTextClassifier(torch.nn.Module):
    def __init__(self,
                 opt,
                 context_embedder: ContextEmbedderBase,
                 emission_scorer: EmissionScorerBase,
                 decoder: torch.nn.Module,
                 config: dict = None,  # store necessary setting or none-torch params
                 emb_log: str = None):
        super(FewShotTextClassifier, self).__init__()
        self.opt = opt
        self.context_embedder = context_embedder
        self.emission_scorer = emission_scorer
        self.decoder = decoder
        self.no_embedder_grad = opt.no_embedder_grad
        self.config = config
        self.emb_log = emb_log

    def forward(
            self,
            test_reps: torch.Tensor,
            test_output_mask: torch.Tensor,
            support_reps: torch.Tensor,
            support_output_mask: torch.Tensor,
            test_target: torch.Tensor,
            support_target: torch.Tensor,
            support_num: torch.Tensor,
            is_training: bool = True,
    ):
        """
        :param test_reps: (batch_size, test_len, emb_dim)
        :param test_output_mask: (batch_size, test_len)
        :param support_reps: (batch_size, support_size, support_len, emb_dim)
        :param support_output_mask: (batch_size, support_size, support_len)
        :param test_target: index targets (batch_size, multi-label_num)
        :param support_target: one-hot targets (batch_size, support_size, multi-label_num, num_tags)
        :param support_num: (batch_size, 1)
        :param is_training: the training mode
        :return:
        """
        # calculate emission: shape(batch_size, 1, no_pad_num_tag)
        test_output_mask = torch.ones(test_output_mask.shape[0], 1).to(test_output_mask.device)  # for sc, each test has only 1 output
        emission = self.emission_scorer(test_reps, support_reps, test_output_mask, support_output_mask, support_target)
        logits = emission

        # as we remove pad label (id = 0), so all label id sub 1. And relu is used to avoid -1 index
        test_target = torch.nn.functional.relu(test_target - 1)
        loss, prediction = torch.FloatTensor(0).to(test_target.device), None

        if is_training:
            loss = self.decoder.forward(logits=logits, mask=test_output_mask, tags=test_target)
        else:

            prediction = self.decoder.decode(logits=logits)
            # we block pad label(id=0) before by - 1, here, we add 1 back
            prediction = self.add_back_pad_label(prediction)
        if is_training:
            return loss
        else:
            return prediction

    def add_back_pad_label(self, predictions: List[List[int]]):
        for pred in predictions:
            for ind, l_id in enumerate(pred):
                pred[ind] += 1  # pad token is in the first place
        return predictions


class SchemaFewShotTextClassifier(FewShotTextClassifier):
    def __init__(
            self,
            opt,
            context_embedder: ContextEmbedderBase,
            emission_scorer: EmissionScorerBase,
            decoder: torch.nn.Module,
            config: dict = None,  # store necessary setting or none-torch params
            emb_log: str = None):
        super(SchemaFewShotTextClassifier, self).__init__(
            opt, context_embedder, emission_scorer, decoder, config, emb_log)

    def forward(
            self,
            test_reps: torch.Tensor,
            test_output_mask: torch.Tensor,
            support_reps: torch.Tensor,
            support_output_mask: torch.Tensor,
            test_target: torch.Tensor,
            support_target: torch.Tensor,
            support_num: torch.Tensor,
            label_reps: torch.Tensor = None,
            is_training: bool = True,
    ):
        """
        few-shot sequence labeler using schema information
        :param test_reps: (batch_size, test_len, emb_dim)
        :param test_output_mask: (batch_size, test_len)
        :param support_reps: (batch_size, support_size, support_len, emb_dim)
        :param support_output_mask: (batch_size, support_size, support_len)
        :param test_target: index targets (batch_size, test_len)
        :param support_target: one-hot targets (batch_size, support_size, support_len, num_tags)
        :param support_num: (batch_size, 1)
        :param label_reps: (batch_size, label_num, emb_dim)
        :param is_training: the training mode
        :return:
        """
        # calculate emission: shape(batch_size, test_len, no_pad_num_tag)
        emission = self.emission_scorer(test_reps, support_reps, test_output_mask, support_output_mask, support_target,
                                        label_reps)
        if not is_training and self.emb_log:
            self.emb_log.write('\n'.join(['test_target\t' + '\t'.join(map(str, one_target))
                                          for one_target in test_target.tolist()]) + '\n')

        logits = emission

        # block pad of label_id = 0, so all label id sub 1. And relu is used to avoid -1 index
        test_target = torch.nn.functional.relu(test_target - 1)

        loss, prediction = torch.FloatTensor([0]).to(test_target.device), None

        if is_training:
            loss = self.decoder.forward(logits=logits, mask=test_output_mask, tags=test_target)
        else:
            prediction = self.decoder.decode(logits=logits)
            # we block pad label(id=0) before by - 1, here, we add 1 back
            prediction = self.add_back_pad_label(prediction)
        if is_training:
            return loss
        else:
            return prediction


def main():
    pass


if __name__ == "__main__":
    main()
