import os
import numpy as np
import pandas as pd
import json
import utils
import re
from tqdm import tqdm

def post_process(values):
    if(len(values) == 0): return values
    #print(values)
    # If all cells in a column span multiple columns with both text and a number, split the column
    # Also if some are already split
    regnum = "(-?\d+(?:\.\d+)?)"
    regwords = "([a-zA-Z\s!-~]+)"
    reg1 = "^\|c=([0-9]+)\|" + regnum + "\s" + regwords + "$"
    reg2 = "^\|c=([0-9]+)\|" + regwords + "\s" + regnum + "$"
    regs = [reg1, reg2]

    for c in range(len(values[0]) - 1):
        start_row = min(len(values), 3) # Number of header rows to start with
        column = [v[c] for v in values[start_row:]]
        #print("Start")
        done = False
        for reg in regs:
            if all(re.match(reg, val) for val in column):
                for r in range(start_row-1, -1, -1): # Check if there are less header rows
                    if re.match(reg, values[r][c]):
                        start_row = r
                        column.insert(0, values[start_row][c])
                for idx, val in enumerate(column):
                    res = re.match(reg, val)
                    cols = int(res.group(1)) - 1
                    val1 = res.group(2)
                    val2 = res.group(3)
                    row = start_row + idx
                    values[row][c] = val1
                    if cols > 1:
                        values[row][c+1] = "|c=%d|%s" % (cols, val2)
                    else:
                        values[row][c+1] = val2
                done = True
                break
        if not done:
            regs2 = [(reg1, regnum, regwords), (reg2, regwords, regnum)]
            for reg in regs2:
                if any(re.match(reg[0], val) for val in column):
                    start_row = 3
                    if match_regex_or_splitted(column, values, start_row, c, reg[0], reg[1], reg[2]):
                        for r in range(start_row-1, -1, -1): # Check if there are less header rows
                            if match_value_regex_or_splitted(values[r][c], values, r, c, reg[0], reg[1], reg[2]):
                                start_row = r
                                column.insert(0, values[start_row][c])
                        for idx, val in enumerate(column):
                            if re.match(reg[0], val):
                                res = re.match(reg[0], val)
                                cols = int(res.group(1)) - 1
                                val1 = res.group(2)
                                val2 = res.group(3)
                                row = start_row + idx
                                values[row][c] = val1
                                if cols > 1:
                                    values[row][c+1] = "|c=%d|%s" % (cols, val2)
                                else:
                                    values[row][c+1] = val2
                        break
    return values

def match_regex_or_splitted(column, values, start_row, col, regex, reg1, reg2):
    for idx, val in enumerate(column):
        if not match_value_regex_or_splitted(val, values, start_row + idx, col, regex, reg1, reg2):
            return False
    return True

def match_value_regex_or_splitted(val, values, row, col, regex, reg1, reg2):
    if re.match(regex, val): return True
    if re.match(reg1, val) and re.match(reg2, values[row][col+1]): return True
    return False


def process_start_ends(row_starts, row_ends, col_starts, col_ends, cells):
    rs = row_starts.copy()
    re = row_ends.copy()
    cs = col_starts.copy()
    ce = col_ends.copy()
    #print("start row process")
    # Remove empty rows
    for r in range(len(row_starts)):
        remove = True
        if r > len(row_ends) - 1 or r > len(row_starts) - 1: # Should never happen
            print("Warning: number of row start coords do not match row end coords (1)")
            break

        rmcells = []
        for cell in cells:
            if cell["rect"][0][1] == row_starts[r] and cell["rect"][1][1] == row_ends[r]:
                if cell["words"] != "":
                    remove = False
                    break
                rmcells.append(cell)

        if remove:
            for cell in rmcells:
                cells.remove(cell)
            for cell in cells:
                if cell["rect"][0][1] == row_starts[r]:
                    new_r = r + 1
                    while row_starts[new_r] not in rs:
                        new_r += 1
                    cell["rect"][0][1] = row_starts[new_r]
                elif cell["rect"][1][1] == row_ends[r]:
                    new_r = r - 1
                    while row_ends[new_r] not in re:
                        new_r -= 1
                    cell["rect"][1][1] = row_ends[new_r]
            rs.remove(row_starts[r])
            re.remove(row_ends[r])

    # Remove empty cols
    for c in range(len(col_starts)):
        remove = True
        if c > len(col_ends) - 1 or c > len(col_starts) - 1: # Should never happen
            print("Warning: number of column start coords do not match column end coords (2)")
            break

        rmcells = []
        for cell in cells:
            if cell["rect"][0][0] == col_starts[c] and cell["rect"][1][0] == col_ends[c]:
                if cell["words"] != "":
                    remove = False
                    break
                rmcells.append(cell)
        if remove:
            for cell in rmcells:
                cells.remove(cell)
            for cell in cells:
                if cell["rect"][0][0] == col_starts[c]:
                    new_c = c + 1
                    if new_c > len(col_ends) - 1 or new_c > len(col_starts) - 1: # Should never happen
                        print("Aborting removing empty columns")
                        return (row_starts, row_ends, col_starts, col_ends, cells)
                    while col_starts[new_c] not in cs:
                        new_c += 1
                    cell["rect"][0][0] = col_starts[new_c]
                elif cell["rect"][1][0] == col_ends[c]:
                    new_c = c - 1
                    while col_ends[new_c] not in ce:
                        new_c -= 1
                    cell["rect"][1][0] = col_ends[new_c]
            cs.remove(col_starts[c])
            ce.remove(col_ends[c])
    return rs, re, cs, ce, cells



def json2csv(json_folder, csv_folder, indicate_merge = False):
    for json_file in os.listdir(json_folder):
        try:
            json_location = os.path.join(json_folder, json_file)
            print(json_location)
            with open(json_location, 'r+', encoding=utils.get_encoding_type(json_location), errors='ignore') as jfile:
                tables = json.load(jfile)

                for table in tables:
                    # print(table["name"])

                    row_starts = sorted(list(set([cell["rect"][0][1] for cell in table["cells"]])))
                    row_ends = sorted(list(set([cell["rect"][1][1] for cell in table["cells"]])))
                    col_starts = sorted(list(set([cell["rect"][0][0] for cell in table["cells"]])))
                    col_ends = sorted(list(set([cell["rect"][1][0] for cell in table["cells"]])))

                    #print("\nsorted row starts: %s" % row_starts)
                    #print("sorted col starts: %s" % col_starts)
                    row_starts, row_ends, col_starts, col_ends, cells = process_start_ends(row_starts, row_ends, col_starts, col_ends, table["cells"])

                    values = [["" for i in range(len(col_starts))] for j in range(len(row_starts))]


                    # Unique occurences of rows and columns
                    for cell in cells:
                        topLeft = cell["rect"][0]
                        botRight = cell["rect"][1]
                        # print("cell: TL: %s BR: %s" % (topLeft, botRight))
                        rowStart = row_starts.index(topLeft[1])
                        rowEnd = row_ends.index(botRight[1])
                        colStart = col_starts.index(topLeft[0])
                        colEnd = col_ends.index(botRight[0])
                        # print("row: %d-%d, col %d-%d | Value: %s" % (rowStart, rowEnd, colStart, colEnd, cell["words"]))
                        numrows = rowEnd - rowStart + 1
                        numcols = colEnd - colStart + 1

                        words = cell["words"]
                        if "," in words:
                            words = '"' + words + '"'

                        if indicate_merge:
                            if numrows > 1 and numcols > 1:
                                values[rowStart][colStart] = "|r=%d|c=%d|%s" % (numrows, numcols, words)
                            elif numrows > 1:
                                values[rowStart][colStart] = "|r=%d|%s" % (numrows, words)
                            elif numcols > 1:
                                values[rowStart][colStart] = "|c=%d|%s" % (numcols, words)
                            else:
                                values[rowStart][colStart] = words
                        else:
                            values[rowStart][colStart] = words
                    values = post_process(values)

                    content = ""
                    for row in values:
                        content += ",".join(row) + "\n"

                    with open(csv_folder + "/" + table["name"] + ".csv", 'w+') as tex_file:
                        tex_file.write(content)
                    # rows = list(set([x["rect"][0][1] for x in table["cells"]]))
                    # columns = list(set([x["rect"][0][0] for x in table["cells"]]))
                    # print("rows %s " % rows)
                    # print("columns: %s " % columns)
                    #(?:\.\d+)
                    # # Replace row/col by their index
                    # index_rows = sorted(list(set([cell["rect"][0][1] for cell in table["cells"]])))
                    # index_columns = sorted(list(set([cell["rect"][0][0] for cell in table["cells"]])))
                    # print("\nsorted rows: %s" % index_rows)
                    # print("sorted cols: %s" % index_columns)

                    # matrix = [['' for _ in range(len(columns))] for _ in range(len(rows))]
                    # for cell in table["cells"]:
                    #     x = index_rows.index(cell["rect"][0][1])
                    #     y = index_columns.index(cell["rect"][0][0])
                    #     matrix[x][y] = cell["words"]
                    #
                    # df = pd.DataFrame(matrix)
                    #
                    # # drop completely empty rows and columns
                    # df = df.replace('', np.nan)
                    # df = df.dropna(how='all', axis=0)
                    # df = df.dropna(how='all', axis=1)
                    # df.to_csv(os.path.join(csv_folder, table["name"]+'.csv'), index=False, header=False)
        except Exception as e:
            print(e)
            continue

if __name__ == '__main__':
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|123 abc", "", "abc", "def"],
    #     ["2", "|c=2|79 mnop", "", "mno", "pqr"],
    #     ["3", "|c=2|78 no", "", "mno", "pqr"],
    #     ["4", "456", "ghi", "ghi", "jkl"],
    #     ["5", "|c=2|789 mno", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|123 abc", "", "abc", "def"],
    #     ["2", "|c=2|79 mnop", "", "mno", "pqr"],
    #     ["3", "|c=2|78 no", "", "mno", "pqr"],
    #     ["4", "ghi", "456", "ghi", "jkl"],
    #     ["5", "|c=2|789 mno", "", "mno", "pqr"]])
    #
    # print(post_process([["Title", "a", "b", "c", "d", "e"],
    #     ["1", "|c=2|abc 123", "", "abc", "|c=2|abc 1", ""],
    #     ["2", "|c=2|ghi 456", "", "abc", "|c=2|ghi 34", ""],
    #     ["3", "mno", "789", "abc", "|c=2|mno 5", ""],
    #     ["4", "|c=2|pqr 789", "", "abc", "|c=2|mno 5", ""],
    #     ["5", "|c=3|stu abc 789", "", "", "|c=2|mno 5", ""]]))

    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|123 abc", "", "abc", "def"],
    #     ["2", "|c=2|456 ghi", "", "ghi", "jkl"],
    #     ["3", "|c=2|789 mno", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|123 abc def ghi", "", "abc", "def"],
    #     ["2", "|c=2|456 ghi jkl", "", "ghi", "jkl"],
    #     ["3", "|c=2|789 mno pqr stu", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|1.23 abc", "", "abc", "def"],
    #     ["2", "|c=2|4.23456 ghi", "", "ghi", "jkl"],
    #     ["3", "|c=2|0.789 mno", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|1.23 abc", "", "abc", "def"],
    #     ["2", "|c=3|4.23456 ghi", "", "", "jkl"],
    #     ["3", "|c=2|0.789 mno", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|abc 123", "", "|c=2|abc 1", ""],
    #     ["2", "|c=2|ghi 456", "", "|c=2|ghi 34", ""],
    #     ["3", "|c=2|mno 789", "", "|c=2|mno 5", ""]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|abc def 123", "", "abc", "def"],
    #     ["2", "|c=2|ghi jkl mno 456", "", "ghi", "jkl"],
    #     ["3", "|c=2|mno pqr stu vwx 789", "", "mno", "pqr"]])
    # post_process([["Title", "a", "b", "c", "d"],
    #     ["1", "|c=2|abc 1.23", "", "abc", "def"],
    #     ["2", "|c=2|ghi 4.23456", "", "ghi", "jkl"],
    #     ["3", "|c=2|mno 0.789", "", "mno", "pqr"]])
    json2csv('json_csv', 'csv')
