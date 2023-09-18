import random
import requests
from bs4 import BeautifulSoup
import time

# List of user-agent strings
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/100.0.0.0 Safari/537.36",
    # Add more user agents as needed
]

# List of proxy servers (example, replace with actual proxy addresses)
proxies = [
    'http://proxy1.example.com:8080',
    'http://proxy2.example.com:8080',
    # Add more proxy addresses as needed
]

# Define a constant for the maximum number of requests per minute
MAX_REQUESTS_PER_MINUTE = 60

# Keep track of the last request time
last_request_time = None

# Function to get a random user-agent
def get_random_user_agent():
    return random.choice(user_agents)

# Function to get a random proxy
def get_random_proxy():
    return random.choice(proxies)

# Function to check and enforce rate limiting
def enforce_rate_limit():
    global last_request_time
    if last_request_time is not None:
        elapsed_time = time.time() - last_request_time
        if elapsed_time < 60:  # Less than 60 seconds (1 minute)
            time.sleep(60 - elapsed_time)  # Wait to ensure rate limit compliance
    last_request_time = time.time()

# Modify the crawl_web function to set user-agent, proxy, and enforce rate limiting for each request
def crawl_web(query):
    # Use Google search URL
    search_url = f"https://www.google.com/search?q={query}"
    
    try:
        enforce_rate_limit()  # Enforce rate limiting before making the request
        
        # Randomly select a user-agent for this request
        headers = {'User-Agent': get_random_user_agent()}
        
        # Randomly select a proxy for this request
        proxy = {'http': get_random_proxy()}
        
        # Send an HTTP GET request with the selected user-agent and proxy
        response = requests.get(search_url, headers=headers, proxies=proxy)
        response.raise_for_status()  # Check for any request errors
        
        # Parse the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search result titles (example)
        result_titles = soup.find_all('h3', class_='t')  # Adjust this based on actual HTML structure
        
        # Format and return the results
        results = "\n".join([title.text for title in result_titles])
        return results
    
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {str(e)}"

# Sample modification to handle IMDb search results (you can adapt this for other websites)
def crawl_imdb(query):
    # Use IMDb search URL
    search_url = f"https://www.imdb.com/find?q={query}&s=tt"
    
    try:
        enforce_rate_limit()  # Enforce rate limiting before making the request
        
        # Randomly select a user-agent for this request
        headers = {'User-Agent': get_random_user_agent()}
        
        # Randomly select a proxy for this request
        proxy = {'http': get_random_proxy()}
        
        # Send an HTTP GET request with the selected user-agent and proxy
        response = requests.get(search_url, headers=headers, proxies=proxy)
        response.raise_for_status()  # Check for any request errors
        
        # Parse the HTML content using BeautifulSoup for IMDb search results
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract search result titles from IMDb (specific to IMDb's structure)
        result_titles = soup.find_all('td', class_='result_text')
        
        # Format and return the results (specific to IMDb)
        results = "\n".join([title.text.strip() for title in result_titles])
        return results
    
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {str(e)}"
