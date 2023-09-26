from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse
import concurrent.futures
import aiohttp
import asyncio
from collections import deque

crawled_count = 0
thread_lock = asyncio.Lock()
queue = deque()

def save_adjacency_matrix_to_file(matrix, filename="adjacency_matrix.txt"):
    """Save the adjacency matrix to a specified file."""
    with open(filename, 'w') as file:
        for url, links in matrix.items():
            file.write(f"{url}\n")
            for link in links:
                file.write(f"  -> {link}\n")
            file.write("\n")

def save_domains_to_file(matrix, filename="domains.txt"):
    """Save the unique domains from the matrix to a specified file."""
    domains = set()
    for url in matrix.keys():
        domain = urlparse(url).netloc
        domains.add(domain)
    with open(filename, 'w') as file:
        for domain in domains:
            file.write(f"{domain}\n")

async def get_links(url):
    """Fetch the webpage asynchronously and return a list of links."""
    try:
        timeout = aiohttp.ClientTimeout(total=5)  # Set a timeout of 5 seconds
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                page_content = await response.text()
                soup = BeautifulSoup(page_content, 'html.parser')

                # Convert relative URLs to absolute URLs
                links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]

                return links
    except Exception as e:
        print(f"Could not fetch URL {url}: {e}")
        return []

async def print_crawled_count():
    global crawled_count
    global queue
    
    while True:
        print(f"Number of pages successfully crawled: {crawled_count}, Remaining in queue: {len(queue)}")
        await asyncio.sleep(5)

async def build_adjacency_matrix(start_url, max_depth=2):
    global crawled_count
    global queue
    
    visited = set()
    queue.clear()
    queue.append((start_url, 0))
    adjacency_matrix = {}

    while queue:
        url, depth = queue.popleft()

        if depth > max_depth:
            continue

        if url not in visited:
            visited.add(url)
            links = await get_links(url)

            if links is not None:
                async with thread_lock:
                    crawled_count += 1
                adjacency_matrix[url] = links

                for link in links:
                    queue.append((link, depth + 1))

    return adjacency_matrix

# Async entry point
async def main():
    start_url = "https://www.scrapingbee.com/blog/crawling-python/"

    # Create a task to print the crawled count
    print_task = asyncio.create_task(print_crawled_count())

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(executor, asyncio.run, build_adjacency_matrix(start_url))
            for _ in range(5)
        ]
        matrix_list = await asyncio.gather(*futures)

    # Merge matrices
    final_matrix = {}
    for matrix in matrix_list:
        final_matrix.update(matrix)

    # Save the matrix and domains
    save_adjacency_matrix_to_file(final_matrix)
    save_domains_to_file(final_matrix)

    # Cancel the print_task once the crawling is complete
    print_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())