import pytest
from aioresponses import aioresponses
from web_crawler_V2 import save_page_details, save_page_links, evaluate_site_quality, is_subdomain, scrape_page

# Mocked website content for testing
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

# Fixture to provide a mocked aiohttp response
@pytest.fixture
def mocked_aiohttp():
    with aioresponses() as mocked:
        yield mocked

# Test for the save_page_details function
@pytest.mark.asyncio
async def test_save_page_details(mocked_aiohttp):
    # Given
    url = 'https://example.com'
    title = 'Example Page'
    headers = 'Header 1 Header 2'

    # When
    mocked_aiohttp.get(url, payload=mocked_html, status=200)
    page_id = await save_page_details(url, title, headers)

    # Then
    assert page_id is not None

# Test for the save_page_links function
@pytest.mark.asyncio
async def test_save_page_links(mocked_aiohttp):
    # Given
    page_id = 1
    links = ['https://example.com/link1', 'https://example.com/link2']

    # When
    mocked_aiohttp.get('https://example.com/link1', payload=mocked_html, status=200)
    mocked_aiohttp.get('https://example.com/link2', payload=mocked_html, status=200)
    await save_page_links(page_id, links)

# Test for the evaluate_site_quality function
def test_evaluate_site_quality():
    # Given
    valid_url = 'https://example.com'
    invalid_url = 'ftp://invalid-url.com'
    
    # When/Then
    assert evaluate_site_quality(valid_url) is True
    assert evaluate_site_quality(invalid_url) is False

# Test for the is_subdomain function
def test_is_subdomain():
    # Given
    url = 'https://sub.example.com'
    domain = 'example.com'
    
    # When/Then
    assert is_subdomain(url, domain) is True

# Test for the scrape_page function
@pytest.mark.asyncio
async def test_scrape_page(mocked_aiohttp):
    # Given
    domain = 'example.com'
    
    # When
    mocked_aiohttp.get('https://example.com', payload=mocked_html, status=200)
    await scrape_page(domain)
