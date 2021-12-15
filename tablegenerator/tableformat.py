from table import Table
import re

class TableFormat():

    def __init__(self):
        self.tex_doc_top = r"""\documentclass{article}\usepackage{multirow}\usepackage{makecell}\usepackage{colortbl}\usepackage[margin=0.5in]{geometry}\usepackage{array}\newcolumntype{W}{!{\color{white} \vrule width 0.4pt}}"""
        self.tex_doc_start = r"""\begin{document}\thispagestyle{empty}\begin{table}"""
        self.tex_doc_end = r"""\end{table}\end{document}"""
        self.tex_colors = r"""\color{white}\arrayrulecolor{red}"""
        #self.tex_colors = r"""\arrayrulecolor{red}"""

    def generate_csv(self, table):
        csv = ""
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row):
                if cell.rows[0] == r_idx and cell.cols[0] == c_idx:
                    n_rows = len(cell.rows)
                    n_cols = len(cell.cols)
                    if n_rows > 1 and n_cols > 1:
                        csv += "|r=" + str(n_rows) + "|c=" + str(n_cols) + "|"
                    elif n_rows > 1:
                        csv += "|r=" + str(n_rows) + "|"
                    elif n_cols > 1:
                        csv += "|c=" + str(n_cols) + "|"
                    content = str(cell.content).replace(" \\\\ ", " ")
                    makecell = r"\\makecell\[([a-z])\]{(.*)}"
                    if reg := re.match(makecell, content):
                        csv += reg.group(2)
                    else:
                        csv += content
                if c_idx < len(row)-1:
                    csv += ","
            csv += "\n"

        return csv

    def generate_table_settings(self, row_height, border_width, text_padding):
        tex_row_height = "\\renewcommand{\\arraystretch}{%f}\n" % row_height
        tex_border_width = "\\setlength{\\arrayrulewidth}{%fpt}\n" % border_width
        tex_text_padding = "\\setlength{\\tabcolsep}{%fpt}\n" % text_padding
        return tex_row_height + tex_border_width + tex_text_padding

    def generate_tex_outlines(self, table):
        table_settings = self.generate_table_settings(table.row_height, 0.4, table.text_padding)

        column_format = table.column_format.copy()
        border_width_compensate = table.border_width - 1 -1.5
        tex_top = r"""\newcolumntype{B}{!{\color{white} \vrule width %fpt}}""" % border_width_compensate

        for i in range(0, len(column_format)):
            if len(column_format[i]) > 0:
                if column_format[i][-1] != '|':
                    column_format[i] = column_format[i][0] + '|'
                elif i > 0:
                    column_format[i] = 'B' + column_format[i]
            elif len(column_format[i]) == 0:
                column_format[i] = '|'
        table_start = "\\begin{tabular}{%s}" % ''.join(column_format)
        table_end = "\\end{tabular}"

        latex = self.generate_tex_table(table, True, column_format)

        return self.tex_doc_top + tex_top + self.tex_doc_start + table_settings + table.font_size + self.tex_colors + table_start + latex + table_end + self.tex_doc_end

    def generate_tex(self, table):
        table_settings = self.generate_table_settings(table.row_height, table.border_width, table.text_padding)
        column_format = table.column_format.copy()
        for i in range(0, len(column_format)):
            if len(column_format[i]) > 0 and column_format[i][-1] != '|':
                column_format[i] = column_format[i][0] + 'W'
            elif len(column_format[i]) == 0:
                column_format[i] = 'W'
        table_start = "\\begin{tabular}{%s}" % ''.join(column_format)
        table_end = "\\end{tabular}"

        latex = self.generate_tex_table(table)

        return self.tex_doc_top + self.tex_doc_start + table_settings + table.font_size + table_start + latex + table_end + self.tex_doc_end


    def generate_tex_table(self, table, all_borders=False, column_format=None):
        if column_format == None: column_format = table.column_format
        latex = "\n"
        invisible_width = table.border_width-0.4
        if (0 in table.h_lines) and all_borders:
            latex += r"""\noalign{\global\arrayrulewidth=%fpt}\arrayrulecolor{white}\hline\noalign{\global\arrayrulewidth=0.4pt}\arrayrulecolor{red} \hline """ % (invisible_width)
        elif (0 in table.h_lines) or all_borders:
            latex += "\hline \n"
        elif not all_borders:
            latex += r"""\noalign{\global\arrayrulewidth=0.4pt}\arrayrulecolor{white}\hline\noalign{\global\arrayrulewidth=%fpt}\arrayrulecolor{black}""" % table.border_width

        for r_idx, row in enumerate(table.rows):
            multirow_cols = []
            for c_idx, cell in enumerate(row):
                n_rows = len(cell.rows)
                n_cols = len(cell.cols)
                is_first_of_multi_col = n_cols > 1 and cell.cols[0] == c_idx
                #is_first_col_of_multi_row = n_rows > 1 and cell.colls[0] == c_idx

                cell_content = str(cell.content)
                if (table.bold_header and r_idx < table.n_headers) or \
                    (table.bold_stub and c_idx < table.n_stubs):
                    cell_content = "\\textbf{%s}" % cell_content

                if is_first_of_multi_col:
                    col_format = ''
                    if c_idx == 0 and (column_format[0] == '|' or all_borders):
                        col_format += '|'
                    col_format += 'c'
                    if all_borders:
                        col_format += '|'
                        next_cell = cell.cols[-1]+1
                        if len(column_format) > next_cell+1 and column_format[next_cell][0] == 'B':
                            col_format += 'B'
                    else:
                        col_format += column_format[cell.cols[-1]+1][1:]

                    latex += "\multicolumn{" + str(n_cols) + "}{%s}{" % col_format

                if n_rows > 1:
                    if cell.rows[0] == r_idx and cell.cols[0] == c_idx:
                        cc = cell_content
                        if cell.vertical:
                            latex += "\parbox[t]{2mm}{\multirow{%d}{*}{\\rotatebox[origin=c]{90}{%s}}}" % (n_rows, cell_content)
                        else:
                            latex += "\multirow{" + str(n_rows) + "}{*}{" + cc + "}"

                    if cell.rows[-1] != r_idx:
                        multirow_cols += [c_idx]
                    #elif cell.cols[0] == c_idx:
                    #    latex += "\multirow{" + str(n_rows) + "}{*}{}"
                elif n_cols == 1 or cell.cols[0] == c_idx:
                    latex += cell_content


                if is_first_of_multi_col:
                    latex += "}"

                if c_idx < len(row)-1 and not(n_cols > 1 and cell.cols[-1] != c_idx):
                    latex += " & "
            #latex += "\\\\[\\arrayrulewidth] \n"

            if (r_idx+1 in table.h_lines) and all_borders and len(multirow_cols) == 0:
                latex += r""" \\[%fpt] """ % (invisible_width)
            else:
                latex += "\\\\"

            if not (r_idx+1 in table.h_lines) and not all_borders:
                latex += r""" \noalign{\global\arrayrulewidth=0.4pt\arrayrulecolor{white}}"""

            if len(multirow_cols) == 0:
                latex += " \hline \n"
            else:
                c_start = 1
                for c_end in multirow_cols:
                    if c_start == c_end+1:
                        c_start = c_end+2
                    else:
                        latex += " \cline{%d-%d}" % (c_start, c_end)
                        c_start = c_end + 2
                if c_start <= len(row):
                    latex += " \cline{%d-%d}" % (c_start, len(row))
                latex += " \n"
            if not (r_idx+1 in table.h_lines) and not all_borders:
                latex += r""" \noalign{\global\arrayrulewidth=%fpt\arrayrulecolor{black}}""" % table.border_width
        return latex
