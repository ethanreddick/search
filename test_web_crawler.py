import pytest
import aiohttp
import aioresponses
from web_crawler import get_links
from web_crawler import save_to_database, retrieve_from_database
from web_crawler import crawl_concurrently

# Mocked website content
mocked_html = """
<html>
    <head></head>
    <body>
        <a href="/relative1">Relative Link 1</a>
        <a href="/relative2">Relative Link 2</a>
        <a href="https://www.external-site.com/absolute">Absolute Link</a>
    </body>
</html>
"""

@pytest.mark.asyncio
async def test_get_links():
    base_url = 'https://example.com'

    # Mock the aiohttp request using aioresponses
    with aioresponses.aioresponses() as mocked:
        mocked.get(base_url, payload=mocked_html, status=200)
        
        # When
        links = await get_links(base_url)
        
        # Then
        assert len(links) == 3  # Ensure we found all links
        assert 'https://example.com/relative1' in links
        assert 'https://example.com/relative2' in links
        assert 'https://www.external-site.com/absolute' in links

@pytest.mark.asyncio
async def test_save_and_retrieve_from_database():
    # Given
    data_to_save = {'url': 'https://example.com', 'title': 'Example Page'}
    
    # When
    await save_to_database(data_to_save)
    retrieved_data = await retrieve_from_database(data_to_save['url'])
    
    # Then
    # Add assertions based on the expected behavior of your database functions
    assert retrieved_data == data_to_save
    # Add more assertions as needed

@pytest.mark.asyncio
async def test_concurrent_crawl():
    base_urls = ['https://example1.com', 'https://example2.com', 'https://example3.com']
    
    # When
    results = await crawl_concurrently(base_urls)
    
    # Then
    # Add assertions based on the expected behavior of your concurrent crawler
    assert len(results) == len(base_urls)
    # Add more assertions as needed