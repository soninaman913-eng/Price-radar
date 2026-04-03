import os
import psycopg2
import yagmail
import cloudscraper
from bs4 import BeautifulSoup
import re

# Setup Scraper and Email
yag = yagmail.SMTP(os.getenv("GMAIL_USER"), os.getenv("GMAIL_PASS"))
scraper = cloudscraper.create_scraper()

def check_prices():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cur = conn.cursor()
        cur.execute("SELECT id, email, url, target_price FROM alerts")
        alerts = cur.fetchall()

        for row_id, email, url, target_price in alerts:
            try:
                res = scraper.get(url, timeout=15)
                soup = BeautifulSoup(res.text, 'html.parser')

                if "amazon" in url:
                    price_str = soup.find("span", {"class": "a-price-whole"}).text
                else:
                    price_str = soup.find("div", {"class": "_30jeq3"}).text

                current_price = int(re.sub(r'[^\d]', '', price_str))

                if current_price <= target_price:
                    yag.send(
                        to=email,
                        subject="🔥 PRICE DROP ALERT!",
                        contents=f"Great news! Your item is now ₹{current_price}.\nBuy here: {url}"
                    )
                    # Remove alert after sending to keep the DB clean
                    cur.execute("DELETE FROM alerts WHERE id = %s", (row_id,))
            except Exception as e:
                print(f"Failed to check {url}: {e}")
                continue

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Worker Error: {e}")

if __name__ == "__main__":
    check_prices()