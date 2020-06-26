import asyncio
from pyppeteer import launch
import requests
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
import sqlite3
import datetime

async def main(url):
    browser = await launch({'headless': True,    # 是否啟用 Headless 模式
                            'devtools': False,    # 否為每一個頁面自動開啟調試工具，默認是 False。如果這個參數設置為 True，那麼 headless 參數就會無效，會被強制設置為 False。
                            'args': [ 
                                '--disable-extensions',
                                '--disable-infobars', # 關閉自動軟體提示info bar
                                '--hide-scrollbars',  # 隱藏屏幕截圖中的滾動條
                                '--disable-bundled-ppapi-flash', # 禁用捆綁的PPAPI版本的Flash
                                '--mute-audio',  # 使發送到音頻設備的音頻靜音，以便在自動測試過程中聽不到聲音
                                '--no-sandbox',           # --no-sandbox 在 docker 里使用时需要加入的参数，不然会报错 (禁用所有通常沙盒化的進程類型的沙盒)
                                '--disable-setuid-sandbox', # Disable the setuid sandbox (Linux only)
                                '--disable-gpu', # 禁用GPU硬件加速。如果沒有軟件渲染器，則GPU進程將不會啟動
                                '--disable-xss-auditor',
                                '--suppress-message-center-popups', # 隱藏所有消息中心通知彈出窗口。用於測試。
                            ],
                            'dumpio': True,               # 解决浏览器多开卡死
                        })

    page = await browser.newPage()
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36')

    js_text = """
            () =>{ 
                Object.defineProperties(navigator,{ webdriver:{ get: () => false } });
                window.navigator.chrome = { runtime: {},  };
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], });
            }
                """
    await page.evaluateOnNewDocument(js_text)  # 本页刷新后值不变，自动执行js
    res = await page.goto(url, options={'waitUntil': 'networkidle0'})

    PAGE_CONTENT_LIST = []
    ## 將每頁內容存入list，爬取 6 頁內容
    pages = 6
    for i in range(pages):
        data = await page.content()
        soup = BeautifulSoup(data, 'html.parser')
        PAGE_CONTENT_LIST.append(soup)
        # 當沒有下一頁時，會出現 keyError
        try:
            onclick_element = soup.select_one("li.next > a")['onclick']
            if onclick_element and i != pages:
                Click_element = await page.querySelector("li.next > a")
                await page.evaluate('(element) => element.click()', Click_element)
                await asyncio.sleep(1)
                await page.evaluate('_ => {window.scrollBy(0, window.innerHeight);}')
        except KeyError as e:
            pass

    await browser.close()

    return PAGE_CONTENT_LIST

def get_Other_Date_Link(link, domain):
    headers = {
    # 'user-agent': ua.random
    'user-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.61 Safari/537.36'
    }
    res = requests.get(link, headers=headers, verify = False, allow_redirects=False, timeout = (10,15))
    soup2 = BeautifulSoup(res.text, 'html.parser')

    return domain + soup2.select_one("li.sign_up_group > a.other_date")['href'].strip()

def do_sql_commend(cur, sql_command):
    cur.execute(sql_command)

if __name__ == '__main__':

    urls = [
        'https://www.newamazing.com.tw/EW/GO/GroupList.asp',
        'https://www.4p.com.tw/EW/GO/GroupList.asp'
    ]
    conn = sqlite3.connect("C:/Users/ACER/Desktop/Interview/01.Interview/Tripresso/Travel.db")
    print("DB連線成功 !")
    cur = conn.cursor()
    drop_table_sql = "DROP TABLE IF EXISTS TWO_TRAVEL_AGENT_TABLE"
    create_table_sql = '''CREATE TABLE TWO_TRAVEL_AGENT_TABLE (
                             PRODUCT_ID VARCHAR(20) PRIMARY KEY NOT NULL,
                             PRODUCT_TYPE VARCHAR(5) NOT NULL,
                             PRODUCT_NAME VARCHAR(50) NOT NULL,
                             PRODUCT_LINK VARCHAR(100) NOT NULL,
                             OTHER_DATE_LINK VARCHAR(100) NOT NULL,
                             PRODUCT_DAYS INT NOT NULL,
                             DEPARTURE_DATE VARCHAR(20) NOT NULL,
                             PRODUCT_PRICE INT NOT NULL,
                             PRODUCT_TOTAL INT NOT NULL,
                             PRODUCT_AVAILABLE INT NULL,
                             TRAVEL_AGENT VARCHAR(10) NOT NULL,
                             DATA_DATE CHAR(8) NOT NULL)'''
    insert_table_sql = "INSERT INTO TWO_TRAVEL_AGENT_TABLE VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    do_sql_commend(cur, drop_table_sql)
    print("DROP_TABLE 成功 !")
    do_sql_commend(cur, create_table_sql)
    print("CREATE_TABLE 成功 !")
    for url in urls:
        counter = 0
        page_counter = 0
        PAGE_CONTENT_LIST = asyncio.get_event_loop().run_until_complete(main(url))
        # 新魅力 一頁20個產品
        # 世邦   一頁12個產品
        # TRAVEL_AGENT 旅行社
        TRAVEL_AGENT = ""
        domain_url = ""
        if "newamazing" in url.lower():
            TRAVEL_AGENT = "新魅力旅遊"
            domain_url = "https://www.newamazing.com.tw"
        elif "4p" in url.lower():
            TRAVEL_AGENT = "世邦旅行社"
            domain_url = "https://www.4p.com.tw"

        for PAGE_CONTENT in PAGE_CONTENT_LIST:
            page_counter += 1
            product_items = PAGE_CONTENT.find("div", {"id": "panel-1"})
            product_items = product_items.select("div.products > div.product.product_item > div.thumbnail")
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
            PRODUCT_ID = ""
            PRODUCT_TYPE = ""
            PRODUCT_NAME = ""
            PRODUCT_LINK = ""
            OTHER_DATE_LINK = ""
            PRODUCT_DAYS = 0
            DEPARTURE_DATE = ""
            PRODUCT_PRICE = 0
            PRODUCT_TOTAL = 0
            PRODUCT_AVAILABLE = 0
            DATA_DATE = ""
            for product_item in product_items:
                # PRODUCT_ID 產品編號
                PRODUCT_ID = product_item.select_one("span.product_num").text.strip()
                # PRODUCT_TYPE 產品種類
                PRODUCT_TYPE = product_item.select_one("div.product_type > span.GO").text.strip()
                # PRODUCT_NAME 產品名稱 (split 換行)
                try:
                    PRODUCT_NAME = product_item.select_one("div.product_name > a").text.splitlines()[2].strip()
                except IndexError:
                    PRODUCT_NAME = product_item.select_one("div.product_name > a").text.strip()
                # PRODUCT_LINK 產品連結
                PRODUCT_LINK = product_item.select_one("div.product_name > a")["href"].strip()
                if "javascript" in PRODUCT_LINK.lower():
                    PRODUCT_LINK = domain_url + PRODUCT_LINK.split("'")[1].strip()
                else:
                    PRODUCT_LINK = domain_url + PRODUCT_LINK
                # OTHER_DATE_LINK 其他時間連結
                OTHER_DATE_LINK = get_Other_Date_Link(PRODUCT_LINK, domain_url)
                # PRODUCT_DAYS 產品天數
                PRODUCT_DAYS = int(product_item.select_one("div.product_days").text.replace("天", "").strip())
                # DEPARTURE_DATE 出發日期
                DEPARTURE_DATE = product_item.select_one("div.product_date").text.strip()
                # PRODUCT_PRICE 產品價錢
                PRODUCT_PRICE = int(product_item.select_one("div.product_price > span > strong").text.replace(",","").strip())
                # PRODUCT_TOTAL 總團位
                PRODUCT_TOTAL = int(product_item.select_one("div.product_total > span.number").text.strip())
                # PRODUCT_AVAILABLE 剩餘團位
                PRODUCT_AVAILABLE = int(product_item.select_one("div.product_available > span.number").text.strip())
                # DATA_DATE 資料時間
                DATA_DATE = str(datetime.date.today()).replace("-", "")
                data = (PRODUCT_ID, 
                        PRODUCT_TYPE, 
                        PRODUCT_NAME, 
                        PRODUCT_LINK, 
                        OTHER_DATE_LINK,
                        PRODUCT_DAYS, 
                        DEPARTURE_DATE, 
                        PRODUCT_PRICE, 
                        PRODUCT_TOTAL,
                        PRODUCT_AVAILABLE,
                        TRAVEL_AGENT,
                        DATA_DATE)
                # print(PRODUCT_ID, " ", TRAVEL_AGENT)
                cur.execute(insert_table_sql, data)
                conn.commit()
                counter += 1
                print("INSERT_TABLE 第", page_counter, "頁，第", counter, "筆 ! ", PRODUCT_ID, " ", TRAVEL_AGENT)

            print("finish !")