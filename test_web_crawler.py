import pytest
import aiohttp
import aioresponses
from web_crawler import get_links

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

