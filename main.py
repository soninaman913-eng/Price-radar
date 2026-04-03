import os
import re
import cloudscraper
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Better headers to bypass bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

scraper = cloudscraper.create_scraper(
    browser={"browser": "chrome", "platform": "windows", "mobile": False}
)

@app.get("/")
async def root():
    return {"status": "PriceRadar API is running!"}

@app.get("/api/track")
async def track_product(url: str = Query(...)):
    try:
        # Use requests with headers for Amazon
        if "amazon" in url:
            res = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")

            title_el = soup.find("span", {"id": "productTitle"})
            if not title_el:
                return {"status": "error", "message": "Amazon is blocking the scraper. Try again in 1 minute."}
            title = title_el.text.strip()

            price_el = soup.find("span", {"class": "a-price-whole"})
            if not price_el:
                price_el = soup.find("span", {"id": "priceblock_ourprice"})
            price_str = price_el.text if price_el else "0"
            price = int(re.sub(r"[^\d]", "", price_str))

        elif "flipkart" in url:
            res = scraper.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")

            # Try multiple Flipkart title selectors
            title_el = (
                soup.find("span", {"class": "B_NuCI"}) or
                soup.find("h1", {"class": "yhB1nd"}) or
                soup.find("span", {"class": "VU-ZEz"})
            )
            if not title_el:
                return {"status": "error", "message": "Flipkart is blocking the scraper. Try again in 1 minute."}
            title = title_el.text.strip()

            # Try multiple Flipkart price selectors
            price_el = (
                soup.find("div", {"class": "_30jeq3"}) or
                soup.find("div", {"class": "Nx9bqj"}) or
                soup.find("div", {"class": "_16Jk6d"})
            )
            price_str = price_el.text if price_el else "0"
            price = int(re.sub(r"[^\d]", "", price_str))

        else:
            return {"status": "error", "message": "Only Amazon and Flipkart URLs are supported."}

        if price == 0:
            return {"status": "error", "message": "Could not find price. The site may be blocking scraping."}

        return {"title": title, "price": price, "status": "success"}

    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/save-alert")
async def save_alert(data: dict):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS alerts (id SERIAL PRIMARY KEY, email TEXT, url TEXT, target_price INT)")
        cur.execute(
            "INSERT INTO alerts (email, url, target_price) VALUES (%s, %s, %s)",
            (data["email"], data["url"], data["target_price"])
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
