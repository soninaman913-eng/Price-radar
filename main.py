import os
import re
import cloudscraper
from bs4 import BeautifulSoup
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2

app = FastAPI()

# Enable CORS so your Vercel Frontend can talk to this Render Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Supabase (PostgreSQL) using Environment Variables
def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

scraper = cloudscraper.create_scraper()

@app.get("/api/track")
async def track_product(url: str = Query(...)):
    try:
        res = scraper.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Scrape Logic for Amazon & Flipkart
        if "amazon" in url:
            title = soup.find("span", {"id": "productTitle"}).text.strip()
            price_element = soup.find("span", {"class": "a-price-whole"})
            price_str = price_element.text if price_element else "0"
            price = int(re.sub(r'[^\d]', '', price_str))
        elif "flipkart" in url:
            title = soup.find("span", {"class": "B_NuCI"}).text.strip()
            price_element = soup.find("div", {"class": "_30jeq3"})
            price_str = price_element.text if price_element else "0"
            price = int(re.sub(r'[^\d]', '', price_str))
        else:
            return {"status": "error", "message": "Store not supported"}

        return {"title": title, "price": price, "status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/save-alert")
async def save_alert(data: dict):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Create table if it doesn't exist (First time only)
        cur.execute("CREATE TABLE IF NOT EXISTS alerts (id SERIAL PRIMARY KEY, email TEXT, url TEXT, target_price INT)")
        cur.execute(
            "INSERT INTO alerts (email, url, target_price) VALUES (%s, %s, %s)",
            (data['email'], data['url'], data['target_price'])
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}