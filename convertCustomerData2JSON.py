import json
import pandas
import datetime

filename = './data.xlsx'
ex_data = pandas.read_excel(filename)

arr = []
for idx, t in enumerate(ex_data.itertuples()):
    if idx < 1:
        continue

    data = {}
    data['company'] = t[1]
    if pandas.isna(data['company']):
        continue

    data['date'] = t[2]
    if pandas.isna(data['date']):
        continue

    data['date'] = datetime.datetime.strptime(data['date'], '%Y.%m.%d')
    data['date'] = data['date'].strftime('%Y-%m')

    data['asset'] = t[3]
    data['upstream'] = t[4]
    data['upstream_dunwei'] = t[5]
    data['buyPrice'] = t[6]
    
    data['kaipiao_dunwei'] = t[8]
    data['upstream_jiesuan_price']= t[9]

    data['downstream'] = t[15]
    data['downstream_dunwei'] = t[16]
    data['sellPrice'] = t[17]

    data['kaipiao_dunwei_trade'] = t[19]
    data['downstream_jiesuan_price'] = t[20]

    arr.append(data)

s = json.dumps(arr)
print(s)

