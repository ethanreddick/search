import requests # Used to fetch the HTML content of a page (GET,POST,DELETE)
from bs4 import BeautifulSoup # Library for parsing HTML documents
import psycopg2 # PostgreSQL database adapter for Python
import queue # Python module that provides a queue implementation
import threading # Python module for working with threads
from urllib.parse import urljoin, urlparse # Allows us to convert all URLs to absolute URLs and parse URLs
from bloom_filter2 import BloomFilter # https://github.com/remram44/python-bloom-filter
import csv # Python's built-in module for processing .csv files
import pickle # Allows for pickling (saving) and de-pickling (loading) of the bloom_filter
import os # Operating system interface used when loading bloom_filter from disk
import time # Required so that the bloom_filter can be saved on a time interval
import logging # For cleaner viewing of the crawling results, I will return only errors
import tempfile # This will be used to ensure the bloom_filter saving will not be corrupted

# Only show errors in the console, not warnings
logging.basicConfig(level = logging.ERROR)

# Database connection setup
def connect_database():
    return psycopg2.connect(
        host = "localhost",
        database = "scraper_db",
        user = "ethan",
        password = "search"
    )

# Collect top-level domains (TLDs) from the .csv file
def read_domains_from_csv(file_name):
    with open(file_name, newline = '') as csvfile:
        reader = csv.reader(csvfile)
        # In the .csv file the domain names are the second entry in each row (second column)
        # Example format of the .csv file is '1,google.com' on the first line
        return [row[1] for row in reader] # This returns each top-level domain name

# Saves page URL, title, and headers to the page_details table in DB
def save_page_details(url, title, headers):
    conn = connect_database()
    cur = conn.cursor()
    # Ensuring all URLs can fit in the DB
    if len(url) > 254: return None
    try:
        cur.execute(
            """
            INSERT INTO page_details (url, title, headers) 
            VALUES (%s, %s, %s) ON CONFLICT (url) DO NOTHING RETURNING id
            """,
            (url, title, headers)
        )
        page_id = cur.fetchone()  # Used so save_page_links can associate links with this page
        conn.commit()
        # Ensure the function either returns the correct page_id or 'None'
        return page_id[0] if page_id else None
    except psycopg2.DatabaseError as e:
        print(f"Database error: {e}")
        return None
    finally:
        cur.close()
        conn.close()
        return page_id

# Saves page links to the page_links table in DB
def save_page_links(page_id, links):
    conn = connect_database()
    cur = conn.cursor()

    for link in links:
        # Ensuring all link entries can fit in the DB
        if len(link) > 254: continue
        cur.execute(
            """
            INSERT INTO page_links (page_id, link) 
            VALUES (%s, %s) ON CONFLICT DO NOTHING
            """,
            (page_id, link)
        )
    conn.commit()
    cur.close()
    conn.close()

# Write the bloom filter to disk so crawler's state can persist after crashes. Saves as .pkl file type.
def save_bloom_filter_state(bloom_filter, file_name):
    # This function creates a temp file and returns a tuple, the 'fd' or file details
    # and the name, which are both used to work with and manipulate the file.
    temp_fd, temp_name = tempfile.mkstemp()
    try:
        # Convert the file descriptor into a python file object.
        # 'wb' means 'write in binary mode', which is what .pkl files use
        with os.fdopen(temp_fd, 'wb') as tmp:
            # Write the bloom_filter as a temporary file
            pickle.dump(bloom_filter, tmp)
        # Once saving as a tmp is complete, replace the old file with the tmp
        os.rename(temp_name, file_name)
    except Exception as e:
        print(f"Error saving the bloom filter: {e}")
        # If an error happens, remove the temp file
        os.remove(temp_name)

# Read the bloom filter from disk for use in the event of a crash TODO: Automatic restart
def load_bloom_filter_state(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'rb') as file:
            return pickle.load(file)
    else: # If no bloom_filter file is found, create a new one and return that
        return BloomFilter(max_elements=100000000, error_rate=0.01)

# Attempts to write the bloom filter to disk periodically
def bloom_filter_periodic_save(bloom_filter, file_name, interval):
    while True:
        save_bloom_filter_state(bloom_filter, file_name)
        time.sleep(interval)

# Attempts to determine if a site is of high quality or if it should be discarded, returns true for quality.
def evaluate_site_quality(url):
    global acceptable_domain_extensions

    # All rules that can cause a site to fail prior to visiting the site
    # Eliminate invalid URLs not starting with 'https://'
    if not url.startswith("https://"): return False
    # Eliminate URLs that contain the hash symbol
    if '#' in url: return False
    # Eliminate URLs that do not have an acceptable domain extension
    if not any(extension in url for extension in acceptable_domain_extensions): return False

    # All other rules
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        # Eliminate sites with a response time above 1 second
        if response.elapsed.total_seconds() > 1: return False
        # Eliminate sites with a response other than an HTML document
        if "text/html" not in response.headers.get('Content-Type', ''): return False
        # Eliminate sites containing unknown characters (\ufffd is unicode for unknown character)
        if '\ufffd' in response.content.decode(response.apparent_encoding, errors = 'replace'): return False
        # Eliminate sites not in English
        if not (soup.find('html') and soup.find('html').get('lang') == 'en'): return False
    except requests.exceptions.ConnectionError as e:
        return False

    return True

# Checks to see if a URL belongs to the same top-level domain
def is_subdomain(url, domain):
    # Parses the url, separates into parts, and checks if the 'network location'
    # or netloc section ends with the given domain name.
    return urlparse(url).netloc.endswith(domain)

# Visits a page and collects the title, headers, and links, and passes them to the DB querying functions.
def scrape_page(domain):
    global crawled_sites_count
    global skipped_sites_count
    global bloom_filter_conflicts
    global checked_urls

    # Initializing a set to store the subdomain queue for this domain
    urls_to_visit = {f"https://{domain}"}

    # For all URLs remaining in the queue
    while urls_to_visit:
        # Pop top URL off the stack
        url = urls_to_visit.pop()
        checked_urls += 1
        # Check each URL against the bloom filter to make sure it hasn't been seen before
        # Also checking to ensure only subdomains are crawled
        if url in bloom_filter or not is_subdomain(url, domain):
            bloom_filter_conflicts += 1
            continue
        # Add the URL to the bloom filter
        bloom_filter.add(url)

        # Only check subdomains that pass the quality check
        if evaluate_site_quality(url):
            try:
                response = requests.get(url) # Sends an HTTP GET request using 'requests'
                soup = BeautifulSoup(response.content, 'html.parser') # Creates the BeautifulSoup object which represents the page document as a nested data structure

                # Getting the title, links, and headers using the BeautifulSoup object
                # Getting the page title if it exists, otherwise setting it to ""
                page_title = soup.title.string if soup.title else ""
                
                # Grabbing all headers, getting their text, and joining them using a space as the delimiter
                headers = ' '.join([header.get_text() 
                for header in soup.find_all(
                    ['h1', 'h2', 'h3']
                    )])
                
                # Collects the links and converts them to absolute URLs using urljoin.
                # Finds all '<a>' anchor elements in the BeautifulSoup object that contain an 'href'
                # attribute (which typically contains a link/URL). Then for each urljoin is used to
                # convert it to an absolute URL, and these are stored in the list 'links'
                links = [
                    urljoin(url, a['href'])
                    for a in soup.find_all(
                        'a', href = True
                        )
                    ]

                # Saves page URL, title, and headers to page_details table in DB
                page_id = save_page_details(url, page_title, headers)
                # Saves page links to page_links table in DB as long as a page_id was returned
                if page_id is not None:
                    save_page_links(page_id, links)
                
                # Debug statement that provides updates
                crawled_sites_count += 1
                dropped_percentage = ((skipped_sites_count + bloom_filter_conflicts) / checked_urls) * 100
                print("URLs checked:", checked_urls, "\nPages crawled:", crawled_sites_count, "\nRejected:", skipped_sites_count, 
                "\nBloom filter conflicts:", bloom_filter_conflicts, f"\n({dropped_percentage :.2f}% total skipped)")
                
                # Only add new subdomain URLs to the queue
                for link in links:
                    if link not in bloom_filter:
                        urls_to_visit.add(link)

            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
        else:
            skipped_sites_count += 1
    return

# The target function for each of the worker threads.
def thread_task(domain_queue):
    # While there are still uncrawled top-level domains
    while not domain_queue.empty():
        try:
            # Attempts to immediately grab the next item from the queue. If somehow the queue is
            # empty even though we *just* checked if it was, it will raise the `queue.Empty` exception.
            # Essentially we want to either grab the next domain if available or move on, but not wait.
            domain = domain_queue.get_nowait()
            scrape_page(domain)
            # Mark the task within the queue as completed
            domain_queue.task_done()
        # Handle the `queue.Empty` exception that could be raised by the `get_nowait()` function
        except queue.Empty:
            break
        except Exception as e:
            print(f"Could not process {domain}: {e}")
            # In this event, we mark the task as complete to remove the domain from the queue and proceed
            domain_queue.task_done()

def main():
    global TLD_CSV_FILE
    global skipped_sites_count
    
    # Initializing the list of top-level domains from the .csv file
    domains_to_visit = read_domains_from_csv(TLD_CSV_FILE)
    print("Finished reading .csv file.")

    # Initialize a queue that will hold the list of all remaining unscraped domains
    domain_queue = queue.Queue()
    # Populate the queue
    for domain in domains_to_visit:
        domain_queue.put(domain)
    print("Finished populating domain queue.")

    # Create a thread to handle periodic saving of the bloom filter with an interval of 30 seconds
    bloom_filter_saving_thread = threading.Thread(
        target = bloom_filter_periodic_save,
        args = (bloom_filter, 'bloom_filter.pkl', 30)
    )
    # Set the thread as a daemon so it will close when the script ends
    bloom_filter_saving_thread.daemon = True
    # Start the thread
    bloom_filter_saving_thread.start()

    # Create and start main body of threads for scraping
    threads = []
    for _ in range(45): # Number of threads defined here
        # When passing arguments to a target function for a thread, a tuple is expected.
        # Even though only the domain_queue is being passed we must 'make it a tuple' with a
        # set of parentheses and a trailing comma.
        thread = threading.Thread(target = thread_task, args = (domain_queue,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish (which will not realistically happen in this case)
    for thread in threads:
        # Here .join() blocks threads until they are all complete
        thread.join()


# CSV File containing the top 1 million most popular top-level-domains https://tranco-list.eu/list/25G99/1000000
TLD_CSV_FILE = './top_million_domains.csv'
acceptable_domain_extensions = [".com", ".net", ".edu", ".org", ".gov", ".mil"]
# Initialized bloom filter with 100M element capactiy and 1% error tolerance
# Read bloom filter from disk
bloom_filter = load_bloom_filter_state('bloom_filter.pkl')
crawled_sites_count = 0
skipped_sites_count = 0
bloom_filter_conflicts = 0
checked_urls = 0

main()