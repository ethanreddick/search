import requests
from bs4 import BeautifulSoup

def search():
    query = search_bar.text()
    bias = bias_selector.currentText()
    results = crawl_web(query)  # Call the web crawling function
    results_display.setPlainText(f"Search query: {query}\nSearch bias: {bias}\n\nResults:\n{results}")

def crawl_web(query):
    # Use Google search URL
    search_url = f"https://www.google.com/search?q={query}"
    
    try:
        # Send an HTTP GET request to the search URL
        response = requests.get(search_url)
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
