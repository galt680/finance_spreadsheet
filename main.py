import re
import bs4
import time
import gspread
import easyimap
import requests
import datetime
import numpy as np
import pandas as pd
from passwords import pswd
from collections import OrderedDict
from my_utils import flatten,split_symbols,time_dec
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)


def get_symbols_email(user,password,host = 'imap.gmail.com', mailbox = "INBOX"):
    imapper = easyimap.connect(host,user,password,mailbox)


    unseen_emails = imapper.unseen()

    symbols_list = []
    for i in unseen_emails:
        if i.title == 'symbols':
            symbols_list.append([i.body])
        else:
            print i.title

    return symbols_list








def get_data_and_filter(symbols):
    scraped_data = {}
    failed_symbols = []
    if isinstance(symbols, (list,tuple)):
        for i in symbols:
            data = requests.get("https://finviz.com/quote.ashx?t=%s"%i)
            soup = bs4.BeautifulSoup(data.text,'lxml')
            try:
                soup.find_all("a",{"class":"tab-link"})[12]
                scraped_data[i] = {'finviz':data}

            except Exception as e:
                print e
                failed_symbols.append(i)
    else:
        data = requests.get("https://finviz.com/quote.ashx?t=%s"%symbols)
        soup = bs4.BeautifulSoup(data.text,'lxml')
        try:
            soup.find_all("a",{"class":"tab-link"})[12]
            scraped_data[symbols] = {'finviz':data}

        except Exception as e:
            print e
            failed_symbols.append(symbols)
    for i in scraped_data.keys():
        try:
            market_watch= requests.get("http://www.marketwatch.com/investing/stock/%s/financials/cash-flow"%i)
            guru_focus_ent = requests.get("http://www.gurufocus.com/stock/%s"%i)
            guru_focus_shiller = requests.get("http://www.gurufocus.com/term/ShillerPE/%s/Shiller-PE-Ratio/"%i)
            scraped_data[i]['market_watch'] = market_watch
            scraped_data[i]['guru_focus_ent'] = guru_focus_ent
            scraped_data[i]['guru_focus_shiller'] = guru_focus_shiller
        except:
            pass
    return scraped_data,failed_symbols



def get_finviz_data(data):
    master = {}
    for i in data:
        soup = bs4.BeautifulSoup(data[i]['finviz'].text,'lxml')
        master[i] = [soup.find_all("a",{"class":"tab-link"})[12].text]
        numbers = soup.find_all('td',{"class":'snapshot-td2'})
        names   = soup.find_all('td',{"class":'snapshot-td2-cp'})
        metrics = ['P/E','PEG','P/B','52W Range','Price','Dividend %']
        for x in enumerate(names):
            if names[x[0]].text in metrics:
                master[str(i)].append(numbers[x[0]].text.split())

    master = pd.DataFrame([flatten(i) for i in master.iteritems()])
    master = master[[0,1,2,3,4,5,7,8,9]]
    master.columns = ['symbol','name','pe','peg','pb','low','high','Dividend','price']
    return master



def get_shiller(data):
    shiller = OrderedDict()
    for i in data:
        try:
            soup = bs4.BeautifulSoup(data[i]['guru_focus_shiller'].text,'lxml')
            shiller[str(i)] = float(re.findall(r'''\d+\.\d+''',str(soup.find_all('div',{"class":"data_value"})[0].text))[0])
        except Exception as e:
            print e,'shiller'
            shiller[str(i)] = np.float64('nan')
    return shiller



def get_fcf(data):
    try:
#         soup = bs4.BeautifulSoup(data[i]['market_watch'].text,'lxml')
        soup = bs4.BeautifulSoup(data.text,'lxml')
        number = (float(re.findall(r'''\d+\.?\d+''',str(soup.find_all("td",{"class":'valueCell'})[-11].text))[0]))
        letter = re.findall(r'''M|B''',str(soup.find_all("td",{"class":'valueCell'})[-11].text))
        number = (float(re.findall(r'''\d+\.?\d+''',str(soup.find_all("td",{"class":'valueCell'})[-12].text))[0]))
        letter = re.findall(r'''M|B''',str(soup.find_all("td",{"class":'valueCell'})[-12].text))
        negative = re.findall(r'''\(''',str(soup.find_all("td",{"class":"valueCell"})[-12].text))
    except Exception as e:
        print e,'fcf'
        return np.float64('nan')
    try:
        if letter[0] == "B":
            number = number*1000000000
        else:
            number = number*1000000
        if negative:
            fcf = -1*number
        else:
             fcf = number
    except Exception as e:

        fcf = number
    return fcf


def get_enterprise(data):
    try:
        soup = bs4.BeautifulSoup(data.text,'lxml')
        a = soup.find_all("th")[2].text
        number = float(re.findall(r'''\d+\.?\d+''',a)[0])
        multip = str(re.findall(r"""M|B""",a)[0])
        if multip == 'B':
            enterprise = number*1000000000
        else:
            enterprise = number*1000000
    except:
        enterprise = np.float64("nan")
    return enterprise



def combine_enter_fcf(data):
    for i in data:
        try:
            yield get_enterprise(data[i]['guru_focus_ent'])/get_fcf(data[i]['market_watch'])
        except:
            yield np.float64('nan')





@time_dec
def make_the_dataframe(list_of_symbols):
    data,failed_symbols = get_data_and_filter(list_of_symbols)
	print failed_symbols
    master = get_finviz_data(data)
    master['Shiller P/E'] = get_shiller(data).values()
    master['Enterprise/FCF Ratio']= [i for i in combine_enter_fcf(data)]
    return master

def numberToLetters(q):
    q = q - 1
    result = ''
    while q >= 0:
        remain = q % 26
        result = chr(remain+65) + result;
        q = q//26 - 1
    return result

def add_to_sheets(dataframe):
    #add header on dataframe to sheets
    columns = dataframe.columns.values.tolist()
    cell_list = sheet.range("A1:"+numberToLetters(len(columns))+'1')
    for cell in cell_list:
        val = columns[cell.col-1]
        if type(val) is str:
            val = val.decode('utf-8')
        cell.value = val
    sheet.update_cells(cell_list)

    #add data from dataframe to sheets
    num_lines,num_columns = dataframe.shape
    cell_list = sheet.range('A2:'+numberToLetters(num_columns)+str(num_lines+1))
    for cell in cell_list:
        val = dataframe.iloc[cell.row-2,cell.col-1]
        try:
            if type(val) is str:
                val = val.decode('utf-8')
            elif isinstance(val, (int, long, float, complex)):
                # note that we round all numbers
                val = int(round(val))
        except Exception as e:
            print e
        cell.value = val
    sheet.update_cells(cell_list)

# list_of_symbols = [i for i in split_symbols(get_symbols_email(user ='routmanapp@gmail.com',password = pswd))]
# master = make_the_dataframe(list_of_symbols).sort_index()
if __name__ == "__main__":
    attemps = 0

    while True:
        try:
            master = make_the_dataframe([i for i in split_symbols(get_symbols_email(user ='routmanapp@gmail.com',password = pswd))])
            name_of_sheet =  "Stock Report " + str((datetime.datetime.now()- datetime.timedelta(hours = 5)).strftime('%Y-%m-%d %H:%M'))
            sheet = client.create(name_of_sheet)
            sheet.share('yaschaffel@gmail.com',perm_type = 'user',role = 'writer')
            # sheet.share('djz@routmanninvestment.com',perm_type = 'user',role = 'writer')
            # sheet.share('Aron.routman@routmanninvestment.com',perm_type = 'user',role = 'writer')
            sheet = client.open(name_of_sheet).sheet1
            add_to_sheets(master.set_index('symbol').sort_index().reset_index())
            print 'success'
        except Exception as e:
            print e
            attemps += 1
            print attemps
        time.sleep(10)
