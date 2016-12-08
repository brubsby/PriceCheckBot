import praw
import time
import sqlite3
import requests
import configparser


#https://www.reddit.com/comments/3cm1p8/how_to_make_your_bot_use_oauth2/
''''USER CONFIGURATION'''
config = configparser.ConfigParser()
config.read('config.ini')
#"sub1+sub2+sub3+..." for multiple
SUBREDDIT = "Test"
#How many posts to retrieve at once, max 100
MAXPOSTS = 100
#Seconds between cycles
WAIT = 600
#API for runedays
INFO_URL = "https://secure.runescape.com/m=itemdb_rs/api/info.json"
CATEGORY_URL = "http://services.runescape.com/m=itemdb_rs/api/catalogue/category.json?category={category}"
CATEGORY_RANGE = range(0, 38)
ITEMS_URL = "http://services.runescape.com/m=itemdb_rs/api/catalogue/items.json?category={category}&alpha={alpha}&page={page}"
DETAIL_URL = "http://services.runescape.com/m=itemdb_rs/api/catalogue/detail.json?item={item}"



def login():
    r = praw.Reddit(config.APP_USERAGENT)
    r.set_oauth_app_info(config.APP_ID, config.APP_SECRET, config.APP_URI)
    r.refresh_access_information(config.APP_REFRESH)
    return r

def getLastRuneDate():
    return requests.get(INFO_URL).json().get("lastConfigUpdateRuneday")

def updateItemsTable():
    sql = sqlite3.connect('sql.db')
    cur = sql.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS runedate(runedate INTEGER)')
    cur.execute('CREATE TABLE IF NOT EXISTS items(id INTEGER, name TEXT)')
    cur.execute('CREATE INDEX IF NOT EXISTS item_index ON items(id)')

    lastRuneDate = getLastRuneDate()
    dbRuneDate = cur.execute('SELECT runedate FROM runedate LIMIT 1;').fetchone()

    if dbRuneDate != None and dbRuneDate[0] < lastRuneDate:
        print('Item Database out of date, updating database from grand exchange api')
        rows = []
        delay = 0
        for category in CATEGORY_RANGE:
            while True:
                try:
                    categoryResponse = requests.get(CATEGORY_URL.format(category=category))
                    time.sleep(delay)
                    categoryJSON = categoryResponse.json()
                except ValueError:
                    delay += 0.025
                    continue
                except Exception as e:
                    print(e)
                    continue
                break
            for alphaDict in categoryJSON.get('alpha'):
                numItems = alphaDict.get('items')
                if numItems > 0:
                    alpha = alphaDict.get('letter').replace('#','%23')
                    itemsRetrieved = 0
                    page = 0
                    while itemsRetrieved < numItems:
                        page += 1
                        while True:
                            try:
                                itemsResponse = requests.get(ITEMS_URL.format(category=category, alpha=alpha, page=page))
                                time.sleep(delay)
                                itemsJSON = itemsResponse.json()
                            except ValueError:
                                delay += 0.025
                                continue
                            except Exception as e:
                                print(e)
                                continue
                            break
                        print("retrieved category={category} alpha={alpha} page={page} at delay={delay}".format(category=category, alpha=alpha, page=page, delay=delay))
                        for itemDict in itemsJSON.get('items'):
                            rows.append((itemDict.get('id'), itemDict.get('name')))
                            itemsRetrieved += 1
        cur.executemany('INSERT OR REPLACE INTO items VALUES (?, ?)', rows)
        cur.execute('INSERT OR REPLACE INTO runedate VALUES (?)', (lastRuneDate,))
        sql.commit()
    else:
        print('Item Database up to date')
updateItemsTable()
