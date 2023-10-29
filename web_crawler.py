from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse
import concurrent.futures
import aiohttp
import asyncio
from collections import deque
import os
import signal

# Current counters
crawled_count = 0
skipped_count = 0
thread_lock = asyncio.Lock()
queue = deque()

# Initial attempt to cut down on unneccessary websites
WHITELIST_KEYWORDS = ["research", "tutorial", "guide", "article", "blog", "study", "insight", "analysis"]
BLACKLIST_KEYWORDS = ["buy now", "special offer", "promo code", "purchase", "shop now", "order now", "buy today"]

MATRIX_FILENAME = "adjacency_matrix.txt"

def save_adjacency_matrix_to_file(matrix, filename=MATRIX_FILENAME):
    print(f"Saving {len(matrix)} URLs to file...")
    with open(filename, 'w') as file:
        for url, links in matrix.items():
            file.write(f"{url}\n")
            for link in links:
                file.write(f"  -> {link}\n")
            file.write("\n")

def save_domains_to_file(matrix, filename="domains.txt"):
    domains = set()
    for url in matrix.keys():
        domain = urlparse(url).netloc
        domains.add(domain)
    with open(filename, 'w') as file:
        for domain in domains:
            file.write(f"{domain}\n")

def load_adjacency_matrix(filename=MATRIX_FILENAME):
    matrix = {}
    current_url = None
    if not os.path.exists(filename):
        return matrix
    with open(filename, 'r') as file:
        for line in file:
            if line.startswith("  -> "):
                matrix[current_url].append(line[5:].strip())
            else:
                current_url = line.strip()
                matrix[current_url] = []
    return matrix

adjacency_matrix = load_adjacency_matrix()

async def get_links(url):
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                page_content = await response.text()
                soup = BeautifulSoup(page_content, 'html.parser')
                links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
                return links
    except Exception as e:
        print(f"Could not fetch URL {url}: {e}")
        return []


async def evaluate_domain(url):
    page_content = await get_links(url)
    if not page_content:
        print(f"No content for URL: {url}")
        return False

    page_content_str = ' '.join(page_content)
    for keyword in WHITELIST_KEYWORDS:
        if keyword in page_content_str:
            print(f"URL passed white list: {url}")
            return True

    for keyword in BLACKLIST_KEYWORDS:
        if keyword in page_content_str:
            print(f"URL failed due to black list: {url}")
            return False

    return True


async def print_crawled_count():
    global crawled_count
    global skipped_count
    global queue
    while True:
        print(f"Pages crawled: {crawled_count}, Skipped domains: {skipped_count}, Remaining in queue: {len(queue)}")
        await asyncio.sleep(5)

async def periodic_save():
    """Periodically save the adjacency matrix."""
    while True:
        await asyncio.sleep(30)  # Save every 5 minutes
        save_count = len(adjacency_matrix)
        save_adjacency_matrix_to_file(adjacency_matrix)
        print(f"Saving {save_count} URLs to file...")

def graceful_shutdown(loop):
    """Save the adjacency matrix and stop the loop."""
    global adjacency_matrix
    save_adjacency_matrix_to_file(adjacency_matrix)
    loop.stop()


async def build_adjacency_matrix(start_url, max_depth=2):
    global crawled_count
    global skipped_count
    global queue
    global adjacency_matrix
    
    visited = set()
    queue.clear()
    queue.append((start_url, 0))

    while queue:
        url, depth = queue.popleft()
        
        if depth > max_depth:
            continue

        if depth == 0 or await evaluate_domain(url):
            if url not in visited:
                visited.add(url)
                links = await get_links(url)
                if links is not None:
                    async with thread_lock:
                        crawled_count += 1
                    adjacency_matrix[url] = links

                    for link in links:
                        queue.append((link, depth + 1))
        else:
            #print(f"Skipped domain: {url}")
            async with thread_lock:
                skipped_count += 1


    print(f"Visited URLs: {len(visited)}, URLs in adjacency matrix: {len(adjacency_matrix)}")

    return adjacency_matrix

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
    global skipped_count
    global queue
    while True:
        print(f"Pages crawled: {crawled_count}, Skipped domains: {skipped_count}, Remaining in queue: {len(queue)}")
        await asyncio.sleep(5)

async def main():
    start_url = "https://www.scrapingbee.com/blog/crawling-python/"
    print_task = asyncio.create_task(print_crawled_count())
    save_task = asyncio.create_task(periodic_save())  # This is new

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, asyncio.run, build_adjacency_matrix(start_url))
            for _ in range(5)
        ]
        matrix_list = await asyncio.gather(*futures)

    global adjacency_matrix
    async with thread_lock:
        for matrix in matrix_list:
            adjacency_matrix.update(matrix)

    save_adjacency_matrix_to_file(adjacency_matrix)
    save_domains_to_file(adjacency_matrix)

    print_task.cancel()
    save_task.cancel()  # Cancel the periodic saving task when done

if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    # Handle shutdown
    for sig in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, sig), graceful_shutdown, loop)

    asyncio.run(main())
