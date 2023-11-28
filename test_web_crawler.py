import pytest
from aioresponses import aioresponses
from web_crawler_V2 import save_page_details, save_page_links, evaluate_site_quality, is_subdomain, save_bloom_filter_state, load_bloom_filter_state
from bloom_filter2 import BloomFilter

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
    # Check if this function indirectly starts the scraping process
    url = 'https://example.com'
    title = 'Example Page'
    headers = 'Header 1 Header 2'
    mocked_aiohttp.get(url, payload=mocked_html, status=200)
    page_id = await save_page_details(url, title, headers)
    assert page_id is not None
