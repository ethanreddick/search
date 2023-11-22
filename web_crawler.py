from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse
import concurrent.futures
import aiohttp
import asyncio
import asyncpg
from collections import deque
import os
import signal
from threading import Lock
import warnings
from bs4 import MarkupResemblesLocatorWarning

warnings.simplefilter('ignore', MarkupResemblesLocatorWarning)

thread_lock = asyncio.Lock()
queue = deque()
save_lock = Lock()
save_interval_seconds = 30   # Save every 30 seconds

in_progress = set()
in_progress_lock = asyncio.Lock()

# Counters
crawled_count = 0
session_crawled_count = 0
skipped_count = 0

# Initial attempt to cut down on unneccessary websites
WHITELIST_KEYWORDS = ["research", "tutorial", "guide", "article", "blog", "study", "insight", "analysis"]
BLACKLIST_KEYWORDS = ["buy now", "special offer", "promo code", "purchase", "shop now", "order now", "buy today"]

DATABASE_URL = "postgresql://ethan:search@localhost:5432/postgres"

async def save_adjacency_matrix_to_db(matrix):
    print("Attempting to save URLs to the database...")
    
    # Check to ensure there's data to save
    if not matrix:
        print("No data to save!")
        return

    # Print the first few items to debug
    print(f"First few items to save: {list(matrix.items())[:3]}")

    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        for url, links in matrix.items():
            await conn.execute('''
                INSERT INTO adjacency_matrix (url, linked_urls) VALUES ($1, $2)
                ON CONFLICT (url) DO UPDATE SET linked_urls = $2
            ''', url, links)
        print(f"Saved {len(matrix)} URLs to the database.")
    except Exception as e:
        print(f"Error saving to database: {e}")
    finally:
        await conn.close()

async def load_adjacency_matrix_from_db():
    conn = await asyncpg.connect(DATABASE_URL)
    matrix = {}
    try:
        rows = await conn.fetch('SELECT url, linked_urls FROM adjacency_matrix')
        for row in rows:
            matrix[row['url']] = row['linked_urls']
    finally:
        await conn.close()
    return matrix

loop = asyncio.get_event_loop()
adjacency_matrix = loop.run_until_complete(load_adjacency_matrix_from_db())

crawled_count = len(adjacency_matrix)
visited = set(adjacency_matrix.keys())
saved_urls = set(adjacency_matrix.keys())

def filter_invalid_links(links):
    """Filter out links that aren't likely to be crawlable web pages."""
    filtered_links = [link for link in links if not link.startswith("mailto:")]
    return filtered_links

async def get_links(url):
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                page_content = await response.text()
                soup = BeautifulSoup(page_content, 'html.parser')
                links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
                links = filter_invalid_links(links)
        return links
    except Exception as e:
        #print(f"Could not fetch URL {url}: {e}")
        return []

async def print_crawled_count():
    global crawled_count
    global skipped_count
    global queue
    while True:
        print(f"Pages crawled: {crawled_count}, Skipped domains: {skipped_count}, Remaining in queue: {len(queue)}")
        await asyncio.sleep(5)

save_lock = asyncio.Lock()

async def periodic_save():

    """Periodically save the adjacency matrix."""
    while True:
        print("Waiting ", save_interval_seconds, "seconds to save...")
        await asyncio.sleep(save_interval_seconds)
        
        print("Attempting to save...")  
        async with save_lock:
            print("Acquired lock for saving...")
            

            if adjacency_matrix:
                print(f"Matrix length: {len(adjacency_matrix)}")
                await save_adjacency_matrix_to_db(adjacency_matrix)
            else:
                print("Matrix is empty!")

            #print(f"Finished saving {len(new_urls_to_save)} URLs to file...")

async def build_adjacency_matrix(start_url, max_depth=2):
    local_visited = set()
    local_adjacency_matrix = {}
    local_queue = deque([(start_url, 0)])
    global crawled_count
    global skipped_count
    global session_crawled_count
    global in_progress

    while local_queue:
        url, depth = local_queue.popleft()

        if depth > max_depth:
            continue

        async with thread_lock:
            if url in in_progress or url in local_visited:
                continue
            in_progress.add(url)
        
        if depth == 0 or await evaluate_domain(url):
            local_visited.add(url)
            links = await get_links(url)
            if links is not None:
                crawled_count += 1
                session_crawled_count += 1
                local_adjacency_matrix[url] = links
                print(f"Added {url} with {len(links)} links to local matrix.")
                
                async with save_lock:
                    adjacency_matrix[url] = links

                for link in links:
                    local_queue.append((link, depth + 1))
        else:
            skipped_count += 1

        async with thread_lock:
            in_progress.remove(url)

    return local_adjacency_matrix

async def evaluate_domain(url):
    page_content = await get_links(url)
    if not page_content:
        return False

    page_content_str = ' '.join(page_content)
    for keyword in WHITELIST_KEYWORDS:
        if keyword in page_content_str:
            return True

    for keyword in BLACKLIST_KEYWORDS:
        if keyword in page_content_str:
            return False

    return True

async def print_crawled_count():
    global crawled_count
    global session_crawled_count
    global skipped_count
    global queue
    while True:
        print(f"Cumulative pages crawled: {crawled_count}, This session: {session_crawled_count}, Skipped domains: {skipped_count}, Remaining in queue: {len(queue)}")
        await asyncio.sleep(5)

async def graceful_shutdown(loop):
    """Save the adjacency matrix and stop the loop."""
    global adjacency_matrix
    await save_adjacency_matrix_to_db(adjacency_matrix)

    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    try:
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
    except Exception as e:
        print(f"Errors during shutdown: {e}")

    loop.stop()

def sync_graceful_shutdown(*args, loop=None):
    loop = loop or asyncio.get_event_loop()
    loop.create_task(graceful_shutdown(loop))

async def main():
    global save_lock
    global thread_lock

    start_url = "https://www.scrapingbee.com/blog/crawling-python/"
    print_task = asyncio.create_task(print_crawled_count())
    save_task = asyncio.create_task(periodic_save())

    futures = [build_adjacency_matrix(start_url) for _ in range(5)]
    matrix_list = await asyncio.gather(*futures)

    global adjacency_matrix
    async with thread_lock:
        for matrix in matrix_list:
            adjacency_matrix.update(matrix)

    print_task.cancel()
    save_task.cancel()  # Cancel the periodic saving task when done

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Handle shutdown
    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), sync_graceful_shutdown, loop)

    asyncio.run(main())
