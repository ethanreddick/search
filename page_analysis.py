import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import aiohttp
import asyncio
import os

DB_NAME = 'web_data.db'
SEM = asyncio.Semaphore(10)  # Limiting the number of concurrent requests
processed_urls_count = 0  # shared variable to keep track of the number of URLs processed
lock = asyncio.Lock()  # a lock to ensure only one task updates processed_urls_count at a time

def setup_database():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS page_data (
            url TEXT PRIMARY KEY,
            content TEXT
        )
        ''')
        conn.commit()

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except ValueError:
        return False

async def extract_content_from_url(url, total_urls):
    global processed_urls_count
    if not is_valid_url(url):
        print(f"Progress: {processed_urls_count/total_urls*100:.2f}% - Invalid URL: {url}")
        return

    async with SEM:  # Ensure we don't hit the limit of concurrent requests
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    page_content = await response.text()
                    soup = BeautifulSoup(page_content, 'html.parser')
                    content = ' '.join([p.text for p in soup.find_all('p')])
                    await store_analysis_in_db(url, content)
                    async with lock:
                        processed_urls_count += 1
                        print(f"Progress: {processed_urls_count/total_urls*100:.2f}% - Stored data for {url}")
        except Exception as e:
            async with lock:
                processed_urls_count += 1
                print(f"Progress: {processed_urls_count/total_urls*100:.2f}% - Error fetching {url}: {e}")

async def store_analysis_in_db(url, content):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO page_data (url, content) VALUES (?, ?)", (url, content))
        conn.commit()

async def process_urls(urls):
    tasks = [extract_content_from_url(url, len(urls)) for url in urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    setup_database()

    if not os.path.exists('adjacency_matrix.txt'):
        print("adjacency_matrix.txt not found!")
    else:
        with open('adjacency_matrix.txt', 'r') as f:
            urls = [line.strip().replace("->", "").strip() for line in f if 'http' in line]

        asyncio.run(process_urls(urls))
