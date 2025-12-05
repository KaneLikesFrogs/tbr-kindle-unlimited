import requests
import random
from bs4 import BeautifulSoup as soup
import csv
import os
import concurrent.futures
import time

def get_headers(): # cycles headers to imitate a more human user-agent
    user_agent_list = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
    ]
    random.shuffle(user_agent_list)
    user_agent = user_agent_list[0]
    headers = {
    "authority": "www.google.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en,en;q=0.9",
    "cache-control": "max-age=0",
    "user-agent": user_agent,
    }
    return headers

def get_response(url,drop_headers = False):
    if drop_headers:
        response = requests.get(url)
    else:
        response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.text
        return(data)
    elif response.status_code == 503:
        time.sleep(1)
        response = requests.get(url, headers=get_headers())
        data = response.text
        return(data)
        # shuffles headers and tries again if error 503 (bot denial)
    else:
        print(f'Error {response.status_code} occured at : {url} Reason: {response.reason}' )
        return ConnectionError

def get_tbr(path): # provide with path to exported storygrpah data(manage account > export storygraph library)
    try:    
        with open(path,encoding = "utf8" ) as file:
            tbr = []
            reader = csv.DictReader(file)
            for row in reader:
                if row['Read Status'] == 'to-read':
                    x = f'{row['Title']} by {row['Authors']}'
                    tbr.append(x)
        print("To-read list found!")
        return(tbr)
    except:
        return Exception

def get_asin_url(item):
    name = item.replace(" ","+")
    name = name.replace("&","%26")
    # sanatises string in for url purposes, may need to make more changes depending on text encoding weirdness
    url = "https://www.amazon.co.uk/s?k=" + name + "&i=stripbooks" # filters to just books
    try:
        data = soup(get_response(url),'html.parser')
    except:
        return
    asinlist = data.select('div[class*="s-asin"]')
    # need to use css selector style here as formatting can be different between different items
    try:
        firstitem = str(asinlist[0])
        start = firstitem.index('data-asin="')
        end = firstitem[start:].index('data-component') + start
        asin = firstitem[start+11:end]
        asin = asin.replace('"',"")
        asin = asin.strip()
    except:
        print(f"\nCould not find asin at {url}")
        return
    ASINurl = f'https://www.amazon.co.uk/exec/obidos/ASIN/{asin}'
    return(ASINurl)

def get_un_availability(name): # would like to try and do an audible plus availbility too but checking audible+ catalogue feels obtuse
    ASINUrl = get_asin_url(name)
    if ASINUrl == None:
        return
    try:
        data = soup(get_response(ASINUrl),'html.parser')
    except:
        return
    prices = data.find_all("span",{"class":"slot-price"})
    for x in prices:
        item = str(x)
        try:
            item.index('"£0.00"')
            item.index('aria-label="With Kindle Unlimited"')
            return(f'{name} : {ASINUrl}')  
        except:
            continue
    return 

def get_tbr_unlimited(path):
    try:
        tbr = get_tbr(path)
    except:
        print("Failed to scan data file")
        return
    chunkedtbr = [tbr[x:x+30] for x in range(0,len(tbr),30)] # chunk response into smaller lists
    available = []
    for tbri in chunkedtbr:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ASINUrls = [executor.submit(get_un_availability,item) for item in tbri]
            for x in concurrent.futures.as_completed(ASINUrls):
                available.append(x.result())
        time.sleep(3)
    return available

path = "ENTER PATH TO SG DATA HERE"
# note that it may be a good idea to avoid spaces along file path and to escape any \ by doubling them up (\\) or replace with /
path = 'C:/Software/StorygraphTBR/abbydata.csv'
available = get_tbr_unlimited(path)
try:
    os.remove("output.txt") 
except FileNotFoundError:
    pass
count = 0
available.sort()
with open("output.txt","a") as file:
    for x in available:
        if x != None:
            count += 1
            print(x)
            file.write(f'{x}\n') # appends to output file
    print(f'{count} results found from {len(get_tbr(path))} books')
    file.write(f'{count} results found from {len(get_tbr(path))} books')
print("Saved to output.txt")