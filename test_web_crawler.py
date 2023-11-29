import pytest
from unittest.mock import patch, MagicMock
# Replace with the actual module name where the crawler functions are defined
import web_crawler_V2
from web_crawler_V2 import *

# Mocking database connection for testing database related functions
@patch('web_crawler_V2.psycopg2.connect')
def test_connect_database(mock_connect):
    web_crawler_V2.connect_database()
    mock_connect.assert_called_once_with(
        host="localhost",
        database="scraper_db",
        user="ethan",
        password="search"
    )

# Testing reading domains from CSV
@patch('builtins.open', new_callable=pytest.mock_open, read_data='1,google.com\n2,example.com')
def test_read_domains_from_csv(mock_open):
    result = web_crawler_V2.read_domains_from_csv('domains.csv')
    assert result == ['google.com', 'example.com']
    mock_open.assert_called_once_with('domains.csv', newline='')

# Testing save_page_details function
@patch('web_crawler_V2.connect_database')
def test_save_page_details(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = [1]

    result = web_crawler_V2.save_page_details(
        "http://example.com", "Example Title", "Header Content")
    assert result == 1
    mock_cursor.execute.assert_called()
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()

# Testing save_page_links function
@patch('web_crawler_V2.connect_database')
def test_save_page_links(mock_connect):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    web_crawler_V2.save_page_links(
        1, ["http://link1.com", "http://link2.com"])
    assert mock_cursor.execute.call_count == 2
    mock_cursor.close.assert_called()
    mock_conn.close.assert_called()

# Testing save_bloom_filter_state function
@patch('web_crawler_V2.os')
@patch('web_crawler_V2.tempfile.mkstemp')
@patch('web_crawler_V2.pickle.dump')
def test_save_bloom_filter_state(mock_dump, mock_mkstemp, mock_os):
    mock_mkstemp.return_value = (None, 'tempfile')
    mock_os.fdopen = MagicMock()

    bloom_filter = MagicMock()
    web_crawler_V2.save_bloom_filter_state(
        bloom_filter, 'bloom_filter.pkl')
    mock_dump.assert_called_with(bloom_filter, mock_os.fdopen())
    mock_os.rename.assert_called_with('tempfile', 'bloom_filter.pkl')

# Testing load_bloom_filter_state function
@patch('web_crawler_V2.os.path.exists')
@patch('web_crawler_V2.pickle.load')
@patch('builtins.open', new_callable=pytest.mock_open)
def test_load_bloom_filter_state(mock_open, mock_load, mock_exists):
    mock_exists.return_value = True
    mock_load.return_value = MagicMock()

    result = web_crawler_V2.load_bloom_filter_state('bloom_filter.pkl')
    mock_open.assert_called_with('bloom_filter.pkl', 'rb')
    assert result is not None

# Testing bloom_filter_periodic_save function
@patch('web_crawler_V2.time.sleep')
@patch('web_crawler_V2.save_bloom_filter_state')
def test_bloom_filter_periodic_save(mock_save, mock_sleep):
    bloom_filter = MagicMock()
    web_crawler_V2.bloom_filter_periodic_save(
        bloom_filter, 'bloom_filter.pkl', 1)
    mock_save.assert_called_with(bloom_filter, 'bloom_filter.pkl')
    mock_sleep.assert_called_with(1)

# Testing evaluate_site_quality function
@patch('web_crawler_V2.requests.get')
def test_evaluate_site_quality(mock_get):
    mock_response = MagicMock()
    mock_response.elapsed.total_seconds.return_value = 0.5
    mock_response.content.decode.return_value = "<html lang='en'></html>"
    mock_response.headers.get.return_value = 'text/html'
    mock_get.return_value = mock_response

    result = web_crawler_V2.evaluate_site_quality("https://example.com")
    assert result == True

# Testing is_subdomain function
def test_is_subdomain():
    assert web_crawler_V2.is_subdomain(
        'http://blog.example.com', 'example.com') == True
    assert web_crawler_V2.is_subdomain(
        'http://anotherdomain.com', 'example.com') == False

# Testing thread_task function
@patch('web_crawler_V2.scrape_page')
@patch('queue.Queue.get_nowait')
def test_thread_task(mock_get_nowait, mock_scrape_page):
    mock_get_nowait.return_value = 'example.com'
    domain_queue = MagicMock()
    domain_queue.empty.return_value = False

    web_crawler_V2.thread_task(domain_queue)
    mock_scrape_page.assert_called_with('example.com')
