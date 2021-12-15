import sys
import os
import json
import subprocess
import string
import numpy as np
from functools import partial
from multiprocessing import Pool
from pad import pad_image
from random import randrange, randint, getrandbits, choice, sample
from table import Table, TableCell
from tableformat import TableFormat
from pprint import pprint
from nltk.corpus import words
import argparse
import textboxtract

def generate_special_table():
    n_rows = randint(2, 15)
    n_columns = randint(2, 8)
    n_text_columns = 0 if randrange(100) < 70 else randint(1, n_columns)
    table_type = {}

    special_choice = randrange(100)
    if special_choice < 30: # irregular headers
        header_choice = randrange(100)
        if header_choice < 33: # first header spans all columns
            n_head = 1
            n_subs = [randint(4,9)]
        elif header_choice < 66: # headers with different number of subheaders
            n_head = randint(1,3)
            n_subs = [randint(2,5) for i in range(n_head)]
        else:
            n_head = randint(1,3) # headers with stable number of subheaders
            n = randint(2,5)
            n_subs = [n for i in range(n_head)]
        table_type['n_headers'] = 2
        table_type['n_stubs'] = randint(1,2)
        n_columns = sum(n_subs)
        n_text_columns = 0 if randrange(100) < 70 else randint(1, n_columns)
        table = Table(table_type, n_rows, n_columns, n_text_columns)
        title_words = sample(words.words(), table_type['n_headers'] * n_columns)
        row0 = []
        row1 = []
        for stub in range(table_type['n_stubs']):
            row0.append(table.rows[0][stub])
            row1.append(table.rows[1][stub])
        start_c = table_type['n_stubs']
        borders = [start_c]
        for h in range(n_head):
            end_c = start_c + n_subs[h]
            content =  title_words.pop(0)
            cell = TableCell(content, [0], list(range(start_c, end_c)))
            for c in range(start_c, end_c):
                row0.append(cell)
            start_c += n_subs[h]
            borders += [start_c]
        table.v_lines = list(set(table.v_lines + borders))
        table.column_format = table.generate_column_format()
        c = 0
        for h in range(n_head):
            for s in range(n_subs[h]):
                content =  title_words.pop(0)
                row1.append(TableCell(content, [1], [c]))
                c += 1
        table.rows[0] = row0
        table.rows[1] = row1
    elif special_choice < 50: # irregular stubs
        stub_choice = randrange(100)
        vert = False
        n_headers = randint(0,2)
        if stub_choice < 70: # stubs with the same number of substubs
            n_stub = randint(1,4)
            n = randint(2,5)
            n_subs = [n for i in range(n_stub)]
        else: # stubs with different number of substubs
            n_stub = randint(1,4)
            n_subs = [randint(2,5) for i in range(n_stub)]
        # else: Rotated (vertical) text cannot be converted to PNG correctly (PDF works)
        #     n_stub = randint(1,3)
        #     n = randint(4,5)
        #     n_subs = [n for i in range(n_stub)]
        #     vert = True
        #     n_headers = 0
        table_type['n_headers'] = n_headers
        table_type['n_stubs'] = 2
        n_rows = sum(n_subs)
        table = Table(table_type, n_rows, n_columns, n_text_columns)
        title_words = sample(words.words(), table_type['n_stubs'] * n_rows)

        start_r = table_type['n_headers']
        borders = [start_r]
        for r in range(n_stub):
            end_r = start_r + n_subs[r]
            content = title_words.pop(0)
            cell = TableCell(content, list(range(start_r, end_r)), [0])
            if vert:
                cell.vertical = True
            for s in range(n_subs[r]):
                table.rows[start_r+s][0] = cell
                table.rows[start_r+s][1] = TableCell(title_words.pop(0), [start_r+s], [1])
            start_r = end_r
            borders += [start_r]
        table.h_lines = list(set(table.h_lines + borders))

    elif special_choice < 85: # Characters: ±, =, /, -, (, ), +
        n_headers = randint(0,2)
        n_stubs = randint(1,2)
        table_type['n_headers'] = n_headers
        table_type['n_stubs'] = n_stubs
        table = Table(table_type, n_rows, n_columns, n_text_columns)
        table.is_regular = True
        table.rows = table.generate_rows()
        cols = sample(list(range(n_stubs, n_stubs + n_columns)), randint(1,n_columns))
        for c in cols:
            number_length = randint(1,5)
            range_start = 10**(number_length-1)
            range_end = (10**number_length)-1

            char = choice(['±', '=', '/', '-', '+', '*', '×', ['[', ']'], ['(', ')'], ['$<$', '$>$']])
            if randrange(100) < 30:
                if len(char) == 2:
                    char[0] = ' %s ' % char[0]
                    char[1] = ' %s ' % char[1]
                else:
                    char = ' %s ' % char

            for r in range(n_headers, n_headers + n_rows):
                c1 = randint(range_start, range_end)
                c2 = randint(range_start, range_end)

                if '*' in char:
                    if randrange(100) < 30:
                        content  = '*'
                    else:
                        content = '%d' % c1
                elif len(char) == 2:
                    content = "%d%s%d%s" % (c1, char[0], c2, char[1])
                else:
                    content = "%d%s%d" % (c1, char, c2)
                table.rows[r][c] = TableCell(content, [r], [c])
    else: # Very small column (with one digit integer)
        n_stubs = 1
        table_type['n_headers'] = 0
        table_type['n_stubs'] = 1
        table = Table(table_type, n_rows, n_columns, n_text_columns)
        table.is_regular = True
        table.rows = table.generate_rows()
        table.text_padding = randint(20, 50)/10
        cols = sample(list(range(n_stubs, n_stubs + n_columns)), randint(1,int(n_columns/2)))
        for c in cols:
            for r in range(n_rows):
                table.rows[r][c] = TableCell("%d" % randrange(10), [r], [c])
    return table


def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def cleanup(dir_name, extension):
    dir_list = os.listdir(dir_name)

    for item in dir_list:
        if not item.endswith(extension):
            filename = os.path.join(dir_name, item)
            if not os.path.isdir(filename):
                os.remove(filename)

def get_amount(path):
    if path[0] == 'train':
        return 1000
    else:
        return 500

def generate(idx, paths, csv_path, png_path, tex_path, pdf_path, aux_path, args):
    tablefm = TableFormat()
    print("Start generating tables")
    for path in np.array(paths).reshape(-1, 2):
        n = get_amount(path)
        for i in range(n):
            done = False
            while not done:
                #table = table_generator.generate()
                table = generate_special_table()
                csv = tablefm.generate_csv(table)

                with open(os.path.join(csv_path, path[0] ,str(idx))+'-'+str(i)+'.csv', 'w+') as csv_file:
                    csv_file.write(csv)

                table_tex = tablefm.generate_tex(table)
                outline_tex = tablefm.generate_tex_outlines(table)

                with open(os.path.join(tex_path, path[0],str(idx))+'-'+str(i)+'.tex', 'w+') as tex_file:
                    tex_file.write(table_tex)

                subprocess.call(['pdflatex', '-interaction=batchmode', '-output-directory', os.path.join(pdf_path, path[0]), os.path.join(tex_path, path[0], str(idx)+'-'+str(i)) + '.tex'])

                subprocess.call('latex -interaction=batchmode -output-directory='+ os.path.join(png_path, path[0]) + ' ' + os.path.join(tex_path, path[0], str(idx)+'-'+str(i)) + '.tex', shell=True, stdout=open(os.devnull, 'wb'))
                subprocess.call('dvipng -q* -T tight -o ' + os.path.join(png_path, path[0], str(idx)+'-'+str(i)) + '.png ' + os.path.join(png_path, path[0], str(idx)+'-'+str(i)) + '.dvi', shell=True, stdout=open(os.devnull, 'wb'))

                with open(os.path.join(tex_path, path[1],str(idx))+'-'+str(i)+'.tex', 'w+') as tex_file:
                    tex_file.write(outline_tex)
                subprocess.call('latex -interaction=batchmode -output-directory='+ os.path.join(png_path, path[1]) + ' ' + os.path.join(tex_path, path[1], str(idx)+'-'+str(i)) + '.tex', shell=True, stdout=open(os.devnull, 'wb'))
                subprocess.call('dvipng -q* -T tight -o ' + os.path.join(png_path, path[1], str(idx)+'-'+str(i)) + '.png ' + os.path.join(png_path, path[1], str(idx)+'-'+str(i)) + '.dvi', shell=True, stdout=open(os.devnull, 'wb'))

                done = True

                if args.padding:
                    try:
                        done = pad_image(os.path.join(png_path, path[0], str(idx)+'-'+str(i)) + '.png', os.path.join(png_path, path[1], str(idx)+'-'+str(i)) + '.png', args.resolution)
                    except:
                        os.remove(os.path.join(png_path, path[0], str(idx)+'-'+str(i)) + '.png')
                        done = False

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--location', type=str, help='Path to save the dataset to.')
    parser.add_argument('--padding', type=bool, default=False, help='Pad images')
    parser.add_argument('--resolution', type=int, default=1024, help='Resolution to pad images to')
    args = parser.parse_args()

    location = args.location

    csv_path = os.path.join(location, 'csv')
    make_dir(csv_path)

    tex_path = os.path.join(location, 'tex')
    make_dir(tex_path)

    png_path = os.path.join(location, 'png')
    make_dir(png_path)

    pdf_path = os.path.join(location, 'pdf')
    make_dir(pdf_path)

    json_path = os.path.join(location, 'json')
    make_dir(json_path)

    paths = ['train', 'train_labels', 'val', 'val_labels', 'test', 'test_labels']
    for idx, path in enumerate(paths):
        new_path_tex = os.path.join(tex_path, path)
        make_dir(new_path_tex)
        new_path_png = os.path.join(png_path, path)
        make_dir(new_path_png)
        if idx % 2 == 0:
            new_path_csv = os.path.join(csv_path, path)
            make_dir(new_path_csv)
            new_path_pdf = os.path.join(pdf_path, path)
            make_dir(new_path_pdf)
            new_path_json = os.path.join(json_path, path)
            make_dir(new_path_json)
    aux_path = os.path.join(location, 'aux-data')
    make_dir(aux_path)

    with open('tabletypes.json') as data_file:
        types = json.load(data_file)

    # for idx, i in enumerate(types):
    #     generate(idx, paths=paths, csv_path=csv_path, png_path=png_path, tex_path=tex_path, pdf_path=pdf_path, aux_path=aux_path, args=args, table_type=i)

    #pool = Pool()
    #pool.starmap(partial(generate, paths=paths, csv_path=csv_path, png_path=png_path, tex_path=tex_path, pdf_path=pdf_path, aux_path=aux_path, args=args), list(enumerate(types)))
    generate(9, paths=paths, csv_path=csv_path, png_path=png_path, tex_path=tex_path, pdf_path=pdf_path, aux_path=aux_path, args=args)
    generate(10, paths=paths, csv_path=csv_path, png_path=png_path, tex_path=tex_path, pdf_path=pdf_path, aux_path=aux_path, args=args)
    generate(11, paths=paths, csv_path=csv_path, png_path=png_path, tex_path=tex_path, pdf_path=pdf_path, aux_path=aux_path, args=args)

    print('Cleaning up')
    for path in np.array(paths).reshape(-1, 2):
        cleanup(os.path.join(png_path, path[0]), '.png')
        cleanup(os.path.join(png_path, path[1]), '.png')
        cleanup(os.path.join(pdf_path, path[0]), '.pdf')

    print('Generating JSON files')
    for idx, path in enumerate(paths):
        if idx % 2 == 0:
            for pdf in os.listdir(os.path.join(pdf_path, path)):
                region_boundary = textboxtract.get_region_boundary(os.path.join(pdf_path, path, pdf))
                data = [{
                    "name": os.path.splitext(pdf)[0],
                    "page": 1,
                    "dpi": 150,
                    "regionBoundary": region_boundary,
                    "renderURL": "validation/png/" + os.path.splitext(pdf)[0] + ".png"
                }]
                with open(os.path.join(json_path, path, os.path.splitext(pdf)[0]+'.json'), 'w') as outfile:
                    json.dump(data, outfile)
    print("Finished")
