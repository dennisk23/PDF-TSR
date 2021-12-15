import random
from pprint import pprint
import numpy as np
import pandas as pd
from random import randrange
from nltk.corpus import words

class TableCell():
    def __init__(self, content, rows, cols, vertical=False):
        self.content = content
        self.rows = rows
        self.cols = cols
        self.vertical = vertical

    def __repr__(self):
        return "TC(r=" + str(self.rows) + ",c=" + str(self.cols) + ")"

class Table():
    def __init__(self, table_type, n_rows, n_columns, n_text_column, max_multi_row=4, max_multi_col=3):
        self.n_headers = table_type["n_headers"]
        self.n_stubs = table_type["n_stubs"]
        # self.indicator_type = table_type["indicator_type"]
        self.n_rows = n_rows
        self.n_columns = n_columns

        self.is_regular = self.randBoolean(60)
        self.header_long_text = self.randBoolean(10)
        self.stub_long_text = self.randBoolean(10)

        self.total_rows = self.n_rows + self.n_headers
        self.total_cols = self.n_columns + self.n_stubs
        self.max_multi_row = max_multi_row
        self.max_multi_col = max_multi_col
        self.n_text_columns = n_text_column

        self.text_column_pos = self.get_text_column_pos()

        self.number_lengths = self.generate_number_lengths()
        self.text_lengths = self.generate_text_lengths()

        all_borders, v_borders, h_borders = self.set_borders()
        self.v_lines = self.generate_v_lines(all_borders, v_borders, h_borders)
        self.h_lines = self.generate_h_lines(all_borders, h_borders, v_borders)
        self.column_format = self.generate_column_format()

        self.row_height = self.generate_row_height()

        self.rows = self.generate_rows()

        # self.product = random.choice([True, False])
        self.bold_stub = random.choice([True, False])
        self.bold_header = random.choice([True, False])

        # self.headers = self.generate_headers()
        # self.stubs = self.generate_stubs()

        # # self.indicator = self.generate_indicator()


        self.text_padding = self.generate_text_padding()
        self.border_width = self.generate_border_width()
        self.font_size = self.generate_font_size()

        # self.df = self.create_df()

    def randBoolean(self, percent):
        return randrange(100) < percent

    def create_df(self):
        # if self.n_stubs > 0 and self.n_headers > 0:
        #     table = pd.DataFrame(data=self.rows, index=self.stubs, columns=self.headers)
        # elif self.n_stubs > 0:
        #     table = pd.DataFrame(data=self.rows, index=self.stubs)
        # elif self.n_headers > 0:
        #     table = pd.DataFrame(data=self.rows, columns=self.headers)
        # else:
        table = pd.DataFrame(data=self.rows, index=self.stubs, columns=self.headers)
        if self.n_stubs > 0:
            table.index = table.index.droplevel(0)
        if self.n_headers > 0:
            table.columns = table.columns.droplevel(0)
        # table = table.sort_index()
        # if self.indicator_type == "stub":
        #     table.index.names = self.indicator
        # elif self.indicator_type == "column":
        #     table.column.names = self.indicator
        # table.sort_index()
        return table

    def generate_indicator(self):
        n = 0
        if self.indicator_type == "stub":
            n = self.n_stubs + 1
        elif self.indicator_type == "column":
            n = self.n_columns + 1
        return random.sample(words.words(), n)

    def generate_stubs(self):
        return pd.MultiIndex.from_arrays([list(range(self.n_rows))] + [random.sample(words.words(), self.n_rows) for x in range(self.n_stubs)])
        # if self.n_stubs > 0:
        #     return pd.MultiIndex.from_arrays(stubs)
        # else:
        # return stubs

    def generate_headers(self):
        return pd.MultiIndex.from_arrays([list(range(self.n_columns))] + [random.sample(words.words(), self.n_columns) for x in range(self.n_headers)])
        # if self.n_headers > 0:
        #     return pd.MultiIndex.from_arrays(headers)
        # else:
        #     return headers

    def generate_row(self, row, rows, picked_words, title_words):
        curRow = [None] * self.total_cols
        current_number_lengths = self.number_lengths.copy()
        current_text_lengths = self.text_lengths.copy()
        for col in range(self.total_cols):
            # Check if previous row contains cell that spans this row
            if len(rows) > 0 and row in rows[row-1][col].rows:
                curRow[col] = rows[row-1][col]
            # Check if this row contains a cell that spans this column
            elif col > 0 and col in curRow[col-1].cols:
                curRow[col] = curRow[col-1]
            else:
                # Make sure a cell spanning multiple rows doesn't go outside headers
                if row < self.n_headers:
                    max_multi_row = self.n_headers - row
                else:
                    max_multi_row = 1 #self.max_multi_row
                # Make sure a cell spanning multiple columns doesn't go outside stubs
                if col < self.n_stubs:
                    max_multi_col = self.n_stubs - col
                else:
                    max_multi_col = 1 #self.max_multi_col
                cell_last_row = row if self.is_regular else min(row + random.randint(0, max_multi_row-1), self.total_rows-1)
                cell_last_col = col if self.is_regular else min(col + random.randint(0, max_multi_col-1), self.total_cols-1)
                if cell_last_col - col > 0:
                    for c in range(cell_last_col, col, -1):
                        # Check if there is a row before and that row has a cell that spans this cell
                        if len(rows) > 0 and row in rows[row-1][c].rows:
                            cell_last_col = c - 1
                # print(row, cell_last_row, ":", col, cell_last_col)
                #print(list(range(row, cell_last_row+1)), list(range(col, cell_last_col+1)))

                content = ""
                if row < self.n_headers or col < self.n_stubs:
                    if self.header_long_text or self.stub_long_text:
                        if row < self.n_headers and col < self.n_stubs:
                            content = title_words[:2]
                            content = title_words.pop(0)
                        elif row < self.n_headers:
                            if self.header_long_text:
                                content = title_words[:2]
                                content = title_words.pop(0)
                            else:
                                content = title_words.pop(0)
                        elif col < self.n_stubs:
                            if self.stub_long_text:
                                content = title_words[:2]
                                content = title_words.pop(0)
                            else:
                                content = title_words.pop(0)
                    else:
                        content = title_words.pop(0)
                elif col - self.n_stubs in self.text_column_pos:
                    length = current_text_lengths[0]
                    align = self.column_format[col+1][0]
                    if length < 0:
                        content = "\\makecell[" + align + "]{" + " ".join(picked_words[0:-length]) + "}"
                    elif length <= 3:
                        content = "\\makecell[" + align + "]{" + " \\\\ ".join(picked_words[0:length]) + "}"
                    elif length <= 5:
                        content = "\\makecell[" + align + "]{" + " ".join(picked_words[:2]) + " \\\\ " + " ".join(picked_words[3:length]) + "}"
                    else:
                        content = "\\makecell[" + align + "]{"
                        acontent = []
                        for w in range(0, length, 5):
                            acontent.append(" ".join(picked_words[w:w+3]))
                        content += " \\\\ ".join(acontent)
                        content += "}"

                    current_text_lengths.pop(0)
                    picked_words.pop(0)
                else:
                    range_start = 10**(current_number_lengths[0]-1)
                    range_end = (10**current_number_lengths[0])-1
                    content = random.randint(range_start, range_end)
                    current_number_lengths.pop(0)

                curRow[col] = TableCell(content, list(range(row, cell_last_row+1)), list(range(col, cell_last_col+1)))
        rows.append(curRow)
        return rows, picked_words, title_words

    def generate_rows(self):
        rows = []
        picked_words = random.sample(words.words(), sum(map(abs, self.text_lengths)) * self.n_rows)
        title_multi = 1
        if self.header_long_text: title_multi *= 2
        if self.stub_long_text: title_multi *= 2
        title_words = random.sample(words.words(), (self.n_headers * self.total_cols + self.n_stubs * self.n_rows) * title_multi)
        for row in range(self.total_rows):
            rows, picked_words, title_words = self.generate_row(row, rows, picked_words, title_words)
        # row = [None] * self.n_columns
        # current_number_lengths = self.number_lengths.copy()
        # current_text_lengths = self.text_lengths.copy()
        # for idx, i in enumerate(row):
        #     if idx in self.text_column_pos:
        #         length = current_text_lengths[0]
        #         row[idx] = "\\makecell{" + " \\\\ ".join(picked_words[0:length]) + "}"
        #         current_text_lengths.pop(0)
        #         picked_words.pop(0)
        #     else:
        #         range_start = 10**(current_number_lengths[0]-1)
        #         range_end = (10**current_number_lengths[0])-1
        #         row[idx] = random.randint(range_start, range_end)
        #         current_number_lengths.pop(0)
        # rows.append(row)
        return rows


    def generate_font_size(self):
        # return r"\scriptsize"
        sizes = [r"\scriptsize", r"\footnotesize", r"\small", r"\normalsize", r"\large", r"\Large", r"\LARGE"]
        if self.total_cols > 7:
            sizes = sizes[:-4]
        elif self.total_cols > 6:
            sizes = sizes[:-3]
        elif self.total_cols > 5:
            sizes = sizes[:-2]
        elif self.total_cols > 4:
            sizes = sizes[:-1]
        elif self.total_cols > 3:
            sizes = sizes[:]
        else:
            sizes = sizes[2:]
        return random.choice(sizes)

    def generate_number_lengths(self):
        return [random.randint(1, 5) for x in range(self.n_columns-self.n_text_columns)]

    def generate_text_lengths(self):
        r = randrange(100)
        lengths = []
        for x in range(self.n_text_columns):
            l = 0
            if self.n_columns < 5:
                if r <= 25:
                    l = - random.randint(2,6) # negative for words without newlines
                elif r <= 50:
                    l = random.randint(3, 18)
                elif r <= 75:
                    l = 1
                else:
                    l = 2
            else:
                if r <= 40:
                    l = 1
                elif r <= 80:
                    l = 2
                else:
                    l = random.randint(3, 6)
            lengths.append(l)
        return lengths
        #return [random.randint(1, 12) if random.choice([True, False, False]) else 1 for x in range(self.n_text_columns)]

    def get_text_column_pos(self):
        return sorted(random.sample(range(self.n_columns), self.n_text_columns))

    def set_rows(self, rows):
        self.rows = rows

    def generate_column_format(self):
        column_format = [''] + np.random.choice(['r', 'c', 'l'], self.n_columns + self.n_stubs, replace=True).tolist()
        for i in self.v_lines:
             column_format[i] += '|'
        # column_format = "".join(np.random.choice(['r', 'c', 'l'], self.n_columns+self.n_stubs, replace=True).tolist())
        # for i in sorted(self.v_lines, reverse=True):
        #     column_format = column_format[:i] + '|' + column_format[i:]
        return column_format

    def set_borders(self):
        rb = randrange(100)
        all_borders = random_v_borders = random_h_borders = False
        if rb <= 20:
            all_borders = True
        elif rb <= 40:
            random_v_borders = True
        elif rb <= 60:
            random_v_borders = True
            random_h_borders = True
        elif rb <= 80:
            random_h_borders = True
        return (all_borders, random_v_borders, random_h_borders)
        #return True, False, False
        #return False, False, True

    def generate_v_lines(self, all_borders, random_v_borders, random_h_borders):
        if all_borders:
            return list(range(self.total_cols+1))
        elif random_v_borders:
            borders = list(range(self.n_stubs+1))
            borders += random.sample(range(self.n_stubs+1, self.total_cols+1), random.randint(max(int(self.n_columns/8), 1), int(self.n_columns/2)))
            return borders
        elif random_h_borders and randrange(100) < 20:
            return list(range(self.n_stubs+1))
        else:
            return []

    def generate_h_lines(self, all_borders, random_h_borders, random_v_borders):
        if all_borders:
            return list(range(self.total_rows+1))
        elif random_h_borders:
            borders = list(range(self.n_headers+1))
            borders += random.sample(range(self.n_headers+1, self.total_rows+1), random.randint(max(int(self.n_rows/8), 1), int(self.n_rows/2)))
            return borders
        elif random_v_borders and randrange(100) < 20:
            return list(range(self.n_headers+1))
        else:
            return []

    def generate_row_height(self):
        if any(l > 1 for l in self.text_lengths) :
            return random.randint(25, 35)/10
        return random.randint(10, 20)/10

    def generate_text_padding(self):
        return random.randint(60, 200)/10

    def generate_border_width(self):
        if random.choice([True, False]):
            return 0.4
        else:
            return random.randint(4, 20)/10

    def __repr__(self):
        ret = ""
        for row in self.rows:
            ret += str(row)
        return ret
