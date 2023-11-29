# SEARCH
CS Capstone Project by Ethan Reddick and Justin Nelson exploring internet search and how to improve it.

# Objective
Design and develop a working model demonstrating one or more alternative search approaches for evaluating page-level content and its value.

# Database Setup
PostgreSQL database named 'scraper_db'
	Connect to DB:
	`psql -d postgres`
	`\c scaper_db`

  DB Config:
	CREATE TABLE page_details ( id SERIAL PRIMARY KEY, url VARCHAR(255) UNIQUE NOT NULL, title VARCHAR(255), headers TEXT ); CREATE TABLE page_links ( id SERIAL PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES page_details(id), link VARCHAR(255));

	Schema:
	`page_details` stores the URL, title, and headers of each page.
	`page_links` stores links found on each page, referencing `page_details`.

# Bloom filter setup
Bloom filter implementation used: https://github.com/remram44/python-bloom-filter
(Clone it in the project root directory)

# Top 1 million domains
Download this .csv file and place it in the project root directory.
https://tranco-list.eu/list/25G99/1000000

 # Operation
 Run web_crawler_V2.py to crawl the internet and populate the PostgreSQL database. When you want to use the search engine to look through what the crawler found, run search_gui.py.
