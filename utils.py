import os
import random
import logging

import torch
import numpy as np
from seqeval.metrics import precision_score, recall_score, f1_score

from transformers import BertConfig
from transformers import BertTokenizer

from model import MFF_MN
import sklearn.metrics
MODEL_CLASSES = {
    'bert': (BertConfig, MFF_MN, BertTokenizer),


}
MODEL_PATH_MAP = {
    'bert': 'bert-base-uncased',
}
# --task MixATIS_clean --model_dir MixATIS_model
def change_intent_labels(args):
    return [label.strip() for label in
            open(os.path.join(args.data_dir, args.task, "test_" + args.intent_label_file), 'r', encoding='utf-8')]


def get_intent_labels(args):
    return [label.strip() for label in
            open(os.path.join(args.data_dir, args.task, args.intent_label_file), 'r', encoding='utf-8')]


def get_slot_labels(args):
    return [label.strip() for label in
            open(os.path.join(args.data_dir, args.task, args.slot_label_file), 'r', encoding='utf-8')]


def load_tokenizer(args):
    # return MODEL_CLASSES[args.model_type][2].from_pretrained(args.model_name_or_path_config)
    return MODEL_CLASSES[args.model_type][2].from_pretrained(args.model_name_or_path)


def init_logger():
    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                        datefmt='%m/%d/%Y %H:%M:%S',
                        level=logging.INFO)


def set_seed(args):
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if not args.no_cuda and torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)


def compute_metrics(intent_preds, intent_labels, slot_preds, slot_labels):
    assert len(intent_preds) == len(intent_labels) == len(slot_preds) == len(slot_labels)
    results = {}
    intent_result = get_intent_acc(intent_preds, intent_labels)
    # intent_f1=f1_score(intent_labels,intent_preds)
    slot_result = get_slot_metrics(slot_preds, slot_labels)
    sementic_result = get_sentence_frame_acc(intent_preds, intent_labels, slot_preds, slot_labels)

    results.update(intent_result)
    results.update(slot_result)
    # results.update(intent_f1)
    results.update(sementic_result)
    return results


def multi_compute_metrics(intent_preds, intent_labels, slot_preds, slot_labels, pred_intent_acc, real_intent_acc):
    assert len(intent_preds) == len(intent_labels) == len(slot_preds) == len(slot_labels)
    results = {}
    slot_result = multi_get_slot_metrics(slot_preds, slot_labels)
    intent_result = multi_get_intent_metrics(intent_preds, intent_labels, pred_intent_acc, real_intent_acc)
    sementic_result = mutisemantic_acc(pred_intent_acc, real_intent_acc, slot_preds, slot_labels)
    results.update(intent_result)
    results.update(slot_result)
    results.update(sementic_result)

    return results


def multi_get_sentence_frame_acc(pred_intent_acc, real_intent_acc, slot_preds, slot_labels):
    """For the cases that intent and all the slots are correct (in one sentence)"""
    # Get the intent comparison result
    intent_result = []
    for preds, labels in zip(pred_intent_acc, real_intent_acc):
        assert len(preds) == len(labels)
        one_sent_result = True
        for p, l in zip(preds, labels):
            if p != l:
                one_sent_result = False
                break
        intent_result.append(one_sent_result)
    intent_result = np.array(intent_result)

    # Get the slot comparision result
    slot_result = []
    for preds, labels in zip(slot_preds, slot_labels):
        assert len(preds) == len(labels)
        one_sent_result = True
        for p, l in zip(preds, labels):
            if p != l:
                one_sent_result = False
                break
        slot_result.append(one_sent_result)
    slot_result = np.array(slot_result)

    sementic_acc = np.multiply(intent_result, slot_result).mean()
    return {
        "sementic_frame_acc": sementic_acc
    }


def multi_get_slot_metrics(preds, labels):
    assert len(preds) == len(labels)
    return {
        "slot_precision": precision_score(labels, preds),
        "slot_recall": recall_score(labels, preds),
        "slot_f1": f1_score(labels, preds)
    }


def multi_get_intent_metrics(preds, labels, pred_intent_acc, real_intent_acc):
    assert len(preds) == len(labels)
    # print(labels)
    # print(preds)
    return {
        "intent_f1": sklearn.metrics.f1_score(labels, preds, average='macro'),
        "intent_precision": intent_acc(pred_intent_acc, real_intent_acc),

    }


def get_slot_metrics(preds, labels):
    assert len(preds) == len(labels)
    return {
        "slot_precision": precision_score(labels, preds),
        "slot_recall": recall_score(labels, preds),
        "slot_f1": f1_score(labels, preds)
    }


def get_intent_metrics(preds, labels):
    assert len(preds) == len(labels)
    # print(labels)
    # print(preds)
    return {
        "intent_f1": f1_score(labels, preds),
        "intent_precision": intent_acc(labels, preds),

    }


def get_intent_acc(preds, labels):
    acc = (preds == labels).mean()
    return {
        "intent_acc": acc
    }


def read_prediction_text(args):
    return [text.strip() for text in open(os.path.join(args.pred_dir, args.pred_input_file), 'r', encoding='utf-8')]


def get_sentence_frame_acc(intent_preds, intent_labels, slot_preds, slot_labels):
    """For the cases that intent and all the slots are correct (in one sentence)"""
    # Get the intent comparison result
    intent_result = (intent_preds == intent_labels)

    # Get the slot comparision result
    slot_result = []
    for preds, labels in zip(slot_preds, slot_labels):
        assert len(preds) == len(labels)
        one_sent_result = True
        for p, l in zip(preds, labels):
            if p != l:
                one_sent_result = False
                break
        slot_result.append(one_sent_result)
    slot_result = np.array(slot_result)

    sementic_acc = np.multiply(intent_result, slot_result).mean()
    return {
        "sementic_frame_acc": sementic_acc
    }


def multilabel2one_hot(labels, nums):
    res = [0.] * nums
    if len(labels) == 0:
        return res
    if isinstance(labels[0], list):
        for label in labels[0]:
            res[int(label)] = 1.
        return res
    for label in labels:
        try:
            res[int(label)] = 1.
        except:
            print(int(label))
    return res


def read_file(file_path):
    """ Read data file of given path.

    :param file_path: path of data file.
    :return: list of sentence, list of slot and list of intent.
    """
    texts, slots, intents = [], [], []
    text, slot = [], []

    with open(file_path, 'r', encoding='utf-8') as fr:
        for line in fr.readlines():
            items = line.strip().split()

            if len(items) == 1:
                texts.append(text)
                slots.append(slot)
                if "/" not in items[0]:
                    intents.append(items)
                else:
                    new = items[0].split("/")
                    intents.append([new[1]])

                # clear buffer lists.
                text, slot = [], []

            elif len(items) == 2:
                text.append(items[0].strip())
                slot.append(items[1].strip())
    return texts, slots, intents


# 多意图部分

def mutisemantic_acc(pred_slot, real_slot, pred_intent, real_intent):
    """
    Compute the accuracy based on the whole predictions of
    given sentence, including slot and intent.
    """
    total_count, correct_count = 0.0, 0.0
    for p_slot, r_slot, p_intent, r_intent in zip(pred_slot, real_slot, pred_intent, real_intent):

        if p_slot == r_slot and p_intent == r_intent:
            correct_count += 1.0
        total_count += 1.0

    return {"sementic_frame_acc": 1.0 * correct_count / total_count}


def intent_acc(pred_intent, real_intent):
    total_count, correct_count = 0.0, 0.0
    for p_intent, r_intent in zip(pred_intent, real_intent):

        if p_intent == r_intent:
            correct_count += 1.0
        total_count += 1.0
    # print("correct_count:",correct_count)
    # print("total_count:",total_count)
    return 1.0 * correct_count / total_count