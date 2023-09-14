import random
import requests
from bs4 import BeautifulSoup

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

# Function to get a random user-agent
def get_random_user_agent():
    return random.choice(user_agents)

# Function to get a random proxy
def get_random_proxy():
    return random.choice(proxies)

# Modify the crawl_web function to set user-agent and proxy for each request
def crawl_web(query):
    # Use Google search URL
    search_url = f"https://www.google.com/search?q={query}"
    
    try:
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
