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

class Cell():
    def __init__(self, id, content, rows, cols):
        self.id = id
        self.content = normalize_text(content)
        self.rows = rows
        self.cols = cols

    def __repr__(self):
        return "TC(id=" + str(self.id) + ",content=" + self.content + ",r=" + str(self.rows) + ",c=" + str(self.cols) + ")"

def read_csv(file):
    rows = []
    with open(file, encoding='ISO-8859-1') as csv_file:
        reader = csv.reader(csv_file, delimiter=',')
        for row in reader:
            rows.append(row)
    return rows

def process_csv(matrix):
    reg_rc = "\|r=([0-9]+)\|c=([0-9]+)\|(.*)"
    reg_r = "\|r=([0-9]+)\|(.*)"
    reg_c = "\|c=([0-9]+)\|(.*)"
    id = 0
    table = [[None for _ in range(len(max(matrix, key=len)))] for _ in range(len(matrix))]
    for r,row in enumerate(matrix):
        for c,val in enumerate(row):
            if val == '': continue
            if val[0] == '"' and val[-1] == '"': val = val[1:-2]

            if reg := re.match(reg_rc, val):
                rl = int(reg.group(1)) # row length
                cl = int(reg.group(2)) # column length
                val = reg.group(3) # value
                if len(val) > 0 and val[0] == '"' and val[-1] == '"': val = val[1:-2]
                if len(val) == 0: continue
                cell = Cell(id, val, rl, cl)
                for ri in range(r, r+rl):
                    for ci in range(c, c+cl):
                        if len(table) < ri+1 or len(table[ri]) < ci+1:
                            break
                        table[ri][ci] = cell
            elif reg := re.match(reg_r, val):
                rl = int(reg.group(1))
                val = reg.group(2)
                if len(val) > 0 and val[0] == '"' and val[-1] == '"': val = val[1:-2]
                if len(val) == 0: continue
                cell = Cell(id, val, rl, 1)
                for ri in range(r, r+rl):
                    if len(table) < ri+1:
                        break
                    table[ri][c] = cell
            elif reg := re.match(reg_c, val):
                cl = int(reg.group(1))
                val = reg.group(2)
                if len(val) > 0 and val[0] == '"' and val[-1] == '"': val = val[1:-2]
                if len(val) == 0: continue
                cell = Cell(id, val, 1, cl)
                for ci in range(c, c+cl):
                    if len(table[r]) < ci+1:
                        break
                    table[r][ci] = cell
            else:
                if len(val) > 0 and val[0] == '"' and val[-1] == '"': val = val[1:-2]
                if len(val) == 0: continue
                cell = Cell(id, val, 1, 1)
                table[r][c] = cell
            id+=1

    return table

def get_next_cells(matrix, row_idx, col_idx):
    h = None
    if len(matrix[row_idx]) > col_idx + 1 and matrix[row_idx][col_idx+1] != None:
        h = matrix[row_idx][col_idx+1].content
    v = None
    if len(matrix) > row_idx+1 and matrix[row_idx+1][col_idx] != None:
        v = matrix[row_idx+1][col_idx].content
    return h, v

def get_relations(matrix):
    relations = []
    for r in range(len(matrix)):
        for c in range(len(matrix[r])):
            if(matrix[r][c] == None): continue
            val1 = matrix[r][c].content
            h, v = get_next_cells(matrix, r, c)
            if h != None and h != id:
                relations.append(('h', val1, h))
            if v != None and v != id:
                relations.append(('v', val1, v))
    return relations

def normalize_text(text):
    text = "".join(text.split())
    return re.sub('[^a-zA-Z0-9]', '', text).upper()



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
            result_list.append([path, 0, 0])
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
