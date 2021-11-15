import os
import sys
import pandas as pd
from pprint import pprint
import csv
import numpy as np
import tabula
from tqdm import tqdm
import re
import math
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

def read_csv(file):
    rows = []
    with open(file, encoding='ISO-8859-1') as csv_file:
        reader = csv.reader(csv_file, delimiter=',')
        for row in reader:
            rows.append(row)
    return rows

def normalize_text(text):
    reg_rc = "\|r=[0-9]+\|c=[0-9]+\|(.*)"
    reg_r = "\|r=[0-9]+\|(.*)"
    reg_c = "\|c=[0-9]+\|(.*)"
    if reg := re.match(reg_rc, text):
        text = reg.group(1)
    elif reg := re.match(reg_r, text):
        text = reg.group(1)
    elif reg := re.match(reg_c, text):
        text = reg.group(1)
    text = re.sub('[^a-zA-Z0-9]', '', text).upper()
    return text

def process_csv(matrix):
    for r,row in enumerate(matrix):
        for c,val in enumerate(row):
            if val == '': continue
            if val[0] == '"' and val[-1] == '"': val = val[1:-2]
            val = normalize_text(val)
            if val == '':
                matrix[r][c] = val
                continue
            if val[0] == '"' and val[-1] == '"': val = val[1:-2]
            matrix[r][c] = val

    return matrix

def get_next_cells(matrix, row_idx, col_idx):
    h = None
    if len(matrix[row_idx]) > col_idx + 1 and matrix[row_idx][col_idx+1] != None:
        h = matrix[row_idx][col_idx+1]
    v = None
    if len(matrix) > row_idx+1 and len(matrix[row_idx+1]) > col_idx and matrix[row_idx+1][col_idx] != None:
        v = matrix[row_idx+1][col_idx]
    return h, v

def get_relations(matrix):
    relations = []
    for r in range(len(matrix)):
        for c in range(len(matrix[r])):
            if(matrix[r][c] == None): continue
            val1 = matrix[r][c]
            h, v = get_next_cells(matrix, r, c)
            if h != None:
                relations.append(('h', val1, h))
            if v != None:
                relations.append(('v', val1, v))
    return relations

def calc_adjacency(pred_rel, gt_rel):

    pred_relations = set(pred_rel)
    gt_relations = set(gt_rel)
    intersection = gt_relations.intersection(pred_relations)

    correct_adj_rel = len(intersection)
    total_adj_rel = len(gt_relations)
    detected_adj_rel = len(pred_relations)

    if detected_adj_rel == 0:
        if correct_adj_rel == 0:
            precision = 1
        else:
            precision = 0
    else:
        precision = correct_adj_rel / detected_adj_rel

    if total_adj_rel == 0:
        if correct_adj_rel == 0:
            recall = 1
        else:
            recall = 0
    else:
        recall = correct_adj_rel / total_adj_rel

    return precision, recall

if __name__ == '__main__':
    if(len(sys.argv) < 4):
        print("Missing argument. Usage: <pred location> <ground truth location> <name> .,.,.,")
        exit(-1)

    pred_path = sys.argv[1]
    gt_path = sys.argv[2]
    name = sys.argv[3]
    scores_path = os.path.join(pred_path, 'scores-'+name+'.csv')

    result_list = []
    missed = 0
    for path in tqdm(os.listdir(gt_path)):
        gt_file = os.path.join(gt_path, path[:-4]+'.csv')
        pred_file = os.path.join(pred_path, path[:-4]+'.csv')
        if not os.path.isfile(pred_file):
            missed  += 1
            print('Missed table:', path)
            continue

        # try:
        #gt_file = os.path.join(gt_path, os.path.splitext(path)[0]+'.csv')
        #pred_file = os.path.join(pred_path, os.path.splitext(path)[0]+'.csv')
        #print(path, gt_file, pred_file)

        gt_relations = get_relations(process_csv(read_csv(gt_file)))
        pred_relations = get_relations(process_csv(read_csv(pred_file)))

        precision, recall = calc_adjacency(pred_relations, gt_relations)
        result_list.append([path, precision, recall])

        # except Exception as e:
        #     print('exception', e)
        #     result_list.append([path, 0, 0])
        #     continue

    result_df = pd.DataFrame(result_list, columns=['file', 'precision', 'recall'])

    # grouped = result_df.copy()
    # grouped['category'] = grouped['file'].apply(lambda x: x.split("-")[0])
    # grouped['file'] = grouped['file'].apply(lambda x: x.split("-")[1])


    # grouped = grouped.groupby('category').mean()

    def f1(row):
        if row['precision'] + row['recall'] == 0:
            return 0
        return (row['precision'] * row['recall'] / (row['precision'] + row['recall'])) * 2

    result_df['f1'] = result_df.apply(f1, axis=1)
    result_df.loc['mean'] = result_df.mean()
    result_df.loc['missed'] = {'precision': missed}
    result_df.to_csv(scores_path)
    # grouped.to_csv(os.path.splitext(scores_path)[0] + '-grouped' + '.csv')
