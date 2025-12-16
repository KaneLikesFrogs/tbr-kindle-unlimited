import requests # used to submit web requests
import random # used for shuffling headers when acquiring response to try and avoid err 503/403 
from bs4 import BeautifulSoup as soup # used for distilling web pages 
import concurrent.futures # used for paralellism of submitting web requests
import csv # used for breaking down export file
import time # used for waiting to avoid getting shut out for bot behaviour

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
    # note that above may not be enough to get around other websites anti-bot measures (for repeat calls)
    # however amazon is vast and callous enough to not really care so this generally works for our purposes
    return headers

def get_response(url):
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.text
        return(data)
    retry = 0
    while response.status_code == 503: 
        retry += 1
        time.sleep(0.5) # sleep may be unnecesseary but helps space out requests if being denied
        response = requests.get(url, headers=get_headers())
        if response.status_code ==200:
            data = response.text
            return(data)
        if retry > 5:
            print(f'\nFailed to get a response from {url} after 5 retries {response.status_code},{response.reason}\n')
            return ConnectionRefusedError
        # shuffles headers and tries again if error 503 (bot denial)
        # only retries 5 times 
    else:
        print(f'\nError {response.status_code} occured at : {url} Reason: {response.reason}\n' )
        return ConnectionError

def get_tbr(path): 
    with open(path) as file:
        tbr = []
        cmplxlist = []
        reader = csv.DictReader(file)
        for row in reader:
            if row['Read Status'] == 'to-read':
                x = f'{row['Title']} by {row['Authors']}'
                tbr.append(x) 
    return(tbr)

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
        print(f"\nCould not find asin at {url}\n")
        return
    ASINurl = f'https://www.amazon.co.uk/exec/obidos/ASIN/{asin}'
    return(ASINurl)

def get_availability(name):
    ASINUrl = get_asin_url(name)
    try:
        data = soup(get_response(ASINUrl),'html.parser')
    except:
        return('UNAVAILABLE')
    prices = data.find_all("span",{"class":"slot-price"})
    for x in prices:
        item = str(x)
        try:
            # look for instance of no cost and mention of kindle unlimited in same block
            item.index('"£0.00"')
            item.index('aria-label="With Kindle Unlimited"')
            return(f'{name} : {ASINUrl}')  
        except:
            continue
    return('UNAVAILABLE')


def get_tbr_unlimited(path):
    try:
        tbr = get_tbr(path)
    except:
        print("Failed to scan data file")
        return
    chunkedtbr = [tbr[x:x+30] for x in range(0,len(tbr),30)] # chunk response into smaller lists
    available = []
    count = 0
    total = len(tbr)
    for tbri in chunkedtbr:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            ASINUrls = [executor.submit(get_availability,item) for item in tbri]
            for x in concurrent.futures.as_completed(ASINUrls):
                count += 1
                print("\033[A                             \033[A") # replaces previous line. This prevents overwiting of any errors that get reported too
                print("[" + ("="*round(count/total * 100)) + ("_"*(100 - round(count/total * 100))) +"]") # progress bar in console 
                available.append(x.result())
        time.sleep(0.5)
    return available

def main(): 
    active = True
    while active: # get path
        path = input("Enter path to Storygraph export\n")
        try:
            get_tbr(path)
            active = False
            break
        except Exception as ex:
            print(f"Please enter a valid file path to a storygraph export Error Message : {ex})")
            print("You can export the data by going to 'Manage Account' and scrolling to 'Export Storygraph Library'")
    print("Export recognised!\n")
    available = get_tbr_unlimited(path)
    try:
        dest = path[:path.rindex('/')]
    except:
        dest = path[:path.rindex('\\')+1]
    count = 0
    dest = dest + "KindleCollection.txt"
    with open(dest,"w") as file: 
        for x in available:
            if x != "UNAVAILABLE":
                print(x)
                file.write(x + ' \n')
                count += 1
            else:
                continue
        print(f"{count} results found ({len(available)} books checked)")
        file.write(f'{count} results found from {len(get_tbr(path))} books')
    print(f"File saved to {dest}")
    input("\nHit return/enter key to close this window")

main()