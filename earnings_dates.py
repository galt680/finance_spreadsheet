import bs4
import time
import random
import gspread
import requests
import numpy as np
import pandas as pd
from my_utils import time_dec
from oauth2client.service_account import ServiceAccountCredentials

#this logs into google spreadsheets
#https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

#open the sheet by name
sheet = client.open('Earnings_Dates')

#get specific page of sheet
worksheet = sheet.worksheet('Symbols')

#get symbols from the symbols page
#need the if-i check to get rid of empty strings
symbols = [i for i in worksheet.col_values(1) if i]

#change the sheet to the sheet with the dates
worksheet = sheet.worksheet('Dates')

#iterate over the symbols and get the earning date from nasdaq
#
def get_data():
    
    data = {}
    for symbol in symbols:
        r = requests.get('http://www.nasdaq.com/earnings/report/%s'%symbol)

        soup = bs4.BeautifulSoup(r.text,'lxml')

        data[symbol] = soup.select('h2')[0].text.strip()[-12:]

        time.sleep(random.randrange(5,7))


    #create pandas dataframe using the symbols as the index
    df = pd.DataFrame([i for i in data.values()],index = [i for i in data])
    df.rename(columns ={0:'dates'},inplace = True)

    #use complicated regex to replace the ones without dates yet
    #switch false date to Not Available
    #https://regex101.com/r/bw0KOL/1
    df.dates = df.dates.str.replace('e?n?t\* for [A-Z]{1,4}:','Not Available')


    return df.sort_index()

    


def add_to_sheet(df,index= None,data = None):
    for i in enumerate(df.iterrows()):
        row = i[0] + 2
        sym = i[1][0]
        edate = i[1][1][0]
        
        worksheet.update_cell(row,index,sym)
        worksheet.update_cell(row,data,edate)
    return True




#resort the df to make the dates the index sort by date
#drop the Not Available ones for sorting by date
def resort_index_df(df):
    df = df.reset_index().set_index('dates').sort_index(ascending = True).drop('Not Available')
    #convert index to timestamp from str
    df.index =[i for i in map(lambda x:pd.Timestamp(x),
              df.reset_index().set_index('dates').sort_index(
              ascending = True).drop('Not Available').index)] 
    df.sort_index(ascending = True,inplace = True)
    
    #switch index to str from pd.Timestamp 
    df.index = [[i for i in map(lambda x:str(x)[:-9],df.index)]]
    return df
    
@time_dec
def main():
    df = get_data()
    worksheet.update_cell(1,1,'Symbol')
    worksheet.update_cell(1,2,'Date')
    worksheet.update_cell(1,5,'Date')
    worksheet.update_cell(1,6,'Symbol')
    add_to_sheet(df,index = 1,data = 2)
    add_to_sheet(resort_index_df(df),index = 5,data = 6)    

if __name__ == "__main__":
    main()
    
