from openpyxl import load_workbook
from openpyxl.styles import Border, Side, PatternFill, Font, GradientFill, Alignment


def style_range(ws, cell_range, border=Border(), fill=None, font=None, alignment=None):
    """
    Apply styles to a range of cells as if they were a single cell.

    :param ws:  Excel worksheet instance
    :param range: An excel range to style (e.g. A1:F20)
    :param border: An openpyxl Border
    :param fill: An openpyxl PatternFill or GradientFill
    :param font: An openpyxl Font object
    """

    top = Border(top=border.top)
    left = Border(left=border.left)
    right = Border(right=border.right)
    bottom = Border(bottom=border.bottom)

    first_cell = ws[cell_range.split(":")[0]]
    if alignment:
        ws.merge_cells(cell_range)
        first_cell.alignment = alignment

    rows = ws[cell_range]
    if font:
        first_cell.font = font

    for cell in rows[0]:
        cell.border = cell.border + top
    for cell in rows[-1]:
        cell.border = cell.border + bottom

    for row in rows:
        l = row[0]
        r = row[-1]
        l.border = l.border + left
        r.border = r.border + right
        if fill:
            for c in row:
                c.fill = fill


def paddingAmount(amount):
    return "{:10.2f}".format(amount).replace('.', '')


def daxie(n):
    if n == ' ':
        return ' '

    return ' ' + '零壹贰叁肆伍陆柒捌玖'[int(n)] + ' '


daxieUnit = ['佰', '拾', '万', '仟', '佰', '拾', '元', '角', '分']

import os

items = 5
itemTotal = paddingAmount(1024)
total = paddingAmount(1024 * items)
path = ''

rows = [3, 5, 7, 9, 11, 13, 15]
for row in rows:
    if items <= row:
        path = 'cost-{}.xlsx'.format(row)
        break

cwd = os.getcwd()
wb = load_workbook(cwd + '/xlsx-templates/{}'.format(path))
ws = wb.active

for i in range(items):
    r = str(i + 5)
    ws['B' + r] = 'hello'
    ws['C' + r] = 'world'
    for j, ch in enumerate(itemTotal):
        col = chr(ord('E') + j)
        ws[col + r] = ch

r = 5 + row
for j, ch in enumerate(total):
    col = chr(ord('E') + j)
    ws[col + str(r)] = ch

r = r + 1
daxieText = '金额大写：'
first = True
for index, ch in enumerate(total):
    dx = daxie(ch)
    if first and dx == ' ':
        continue

    first = False
    daxieText = daxieText + daxie(ch) + daxieUnit[index]

ws['B' + str(r)] = daxieText

wb.save('/Users/yangchen/Downloads/export_cost.xlsx')
