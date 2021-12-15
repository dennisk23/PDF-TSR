from operator import itemgetter
from itertools import groupby
import os
import json
import fitz
import sys
import time
import minecart
from tqdm import tqdm

def texboxtract(pdf, tables):
    for table in tables:
        doc = fitz.open(pdf)
        page = doc[int(table["page"])-1]
        words = page.getTextWords()
        for idx, cell in enumerate(table["cells"]):
            rect = [cell[0][0]*0.75+table["regionBoundary"]["x1"], cell[0][1]*0.75+792-table["regionBoundary"]["y1"], cell[1][0]*0.75+table["regionBoundary"]["x1"], cell[1][1]*0.75+792-table["regionBoundary"]["y1"]]

            mywords = [w for w in words if fitz.Rect([(w[0]+w[2])/2,(w[1]+w[3])/2,(w[0]+w[2])/2+1,(w[1]+w[3])/2+1]) in fitz.Rect(rect)]
            mywords.sort(key = itemgetter(3, 0))   # sort by y1, x0 of the word rect
            group = groupby(mywords, key = itemgetter(3))

            result = ""
            for y1, gwords in group:
                result += " ".join(w[4] for w in gwords)
            cell = {"rect": [(rect[0], rect[1]), (rect[2], rect[3])], "words": result}
            table["cells"][idx] = cell
    return tables

def extract(json_folder, pdf_folder):
    for json_file in os.listdir(json_folder):
        json_file_location = os.path.join(json_folder, json_file)
        with open(json_file_location, 'r+') as jfile:
            try:
                start_time = time.time()
                tables = json.load(jfile)
                filename, file_extension  = os.path.splitext(os.path.basename(json_file_location))
                pdf_location = os.path.join(pdf_folder, filename) + ".pdf"
                tables = texboxtract(pdf_location, tables)

                jfile.seek(0)
                jfile.write(json.dumps(tables))
                jfile.truncate()
                elapsed_time = time.time() - start_time
                # print("Took: "+time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
            except Exception as e:
                print(e)
                continue

def get_region_boundary(pdf):
    with open(pdf, 'rb') as fp:
        doc = minecart.Document(fp)
        page = doc.get_page(0)
        shapes = [{"x1":shape.path[0][1], "y1": shape.path[0][2], "x2": shape.path[1][1], "y2": shape.path[1][2]} for shape in page.shapes]
        characters = [{"x1": letter.get_bbox()[0], "y1":letter.get_bbox()[1], "x2": letter.get_bbox()[2], "y2": letter.get_bbox()[3]} for letter in page.letterings]
        combined = shapes + characters
        x1 = min([item['x1'] for item in combined])
        y1 = max([item['y1'] for item in combined])
        x2 = max([item['x2'] for item in combined])
        y2 = min([item['y2'] for item in combined])
        return {"x1": x1, "y1": y2, "x2": x2, "y2": y1} 
