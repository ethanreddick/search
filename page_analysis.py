from bs4 import BeautifulSoup
from urllib.parse import urlparse
import aiohttp
import asyncio
import os
import psycopg2  # PostgreSQL adapter for Python
from psycopg2.pool import SimpleConnectionPool

DATABASE_CONFIG = {
    'dbname': 'template1', # TODO: update this later to real DB
    'user': 'ethan',
    'password': 'search',
    'host': 'localhost',
    'port': '5432'
}
SEM = asyncio.Semaphore(30)  # Limiting the number of concurrent requests
processed_urls_count = 0  # shared varizable to keep track of the number of URLs processed
lock = asyncio.Lock()  # a lock to ensure only one task updates processed_urls_count at a time

connection_pool = SimpleConnectionPool(1, 20, **DATABASE_CONFIG)

batched_data = []

async def store_analysis_in_db(url, content):
    global batched_data
    
    # Check if the URL is already in the batched_data. If so, skip it.
    if any(item for item in batched_data if item[0] == url):
        return
    
    batched_data.append((url, content))
    
    if len(batched_data) >= 100:  # choose an appropriate batch size
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        try:
            args_str = ','.join(cursor.mogrify("(%s,%s)", x).decode("utf-8") for x in batched_data)
            cursor.execute("INSERT INTO page_data (url, content) VALUES " + args_str + " ON CONFLICT (url) DO UPDATE SET content = EXCLUDED.content")
            conn.commit()
            batched_data.clear()
        finally:
            cursor.close()
            connection_pool.putconn(conn)

def setup_database():
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS page_data (
        url TEXT PRIMARY KEY,
        content TEXT
    )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

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


async def process_urls(urls):
    tasks = [extract_content_from_url(url, len(urls)) for url in urls]
    await asyncio.gather(*tasks)

    if batched_data:
        conn = connection_pool.getconn()
        cursor = conn.cursor()
        try:
            args_str = ','.join(cursor.mogrify("(%s,%s)", x).decode("utf-8") for x in batched_data)
            cursor.execute("INSERT INTO page_data (url, content) VALUES " + args_str + " ON CONFLICT (url) DO UPDATE SET content = EXCLUDED.content")
            conn.commit()
        finally:
            cursor.close()
            connection_pool.putconn(conn)


if __name__ == "__main__":
    setup_database()

    if not os.path.exists('adjacency_matrix.txt'):
        print("adjacency_matrix.txt not found!")
    else:
        with open('adjacency_matrix.txt', 'r') as f:
            urls = [line.strip().replace("->", "").strip() for line in f if 'http' in line]

        asyncio.run(process_urls(urls))
