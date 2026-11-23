UCI Information Retrieval Assignment 3
Search Engine

=======================================

This project implements a search engine for the ICS web.

It contains:

1. An indexer that builds an inverted index by crawling HTML/JSON pages.
2. A search engine that accepts user queries and returns relevant urls.
3. An evaluation mode that runs the queries listed in TEST.txt.

1. REQUIREMENTS
---------------

Use python3 and install these dependencies:

python3 -m pip install nltk beautifulsoup4 lxml

2. PROJECT FILES
-----------------

inverter.py - Builds the inverted index by reading JSON files from the ./DEV folder and tokenizing and stemming text.
It writes partial indexes to the disk and merges them into the final index along with the offsets.

norms.py - Streams the final index and creates document length norms used for score normalization.

search.py - Search enging interface on the command line. Loads the offsets and URL data, opens the index file and looks for
query-term postings, ranks documents, and prints the results.

make_report.py - Helper script to produce the top 5 URLS for Milestone 2.

TEST.txt - List of test queries for evaluation. 

3. BUILDING THE INDEX
---------------------

Run "python3 inverter.py" from the project root

The indexer reads all JSON files under ./DEV and extracts the URL and HTML content while skipping duplicate URLS.
It then tokenizes all alphanumeric sequences, lowercases them, leaves stopwords, and applies Porter stemming using NLTK.
It treats text in b, strong, h1, h2, h3, and title as important and stores the term frequency and important-word flag in each posting.
It writes multiple partial index files to the disk and merges the indexs into index.txt and writes the offsets.json and doc_urls.json.

4. CREATING DOCUMENT NORMS
--------------------------

After the index is built, run "python3 norms.py".

This creates the doc_norms.json.

5. RUNNING SINGLE QUERIES
-------------------------

To execute a single query, run 'python3 search.py "QUERY"', where QUERY is the query you would like to search.

For example,

python3 search.py "machine learning" or python3 search.py "cristina lopes"

Results are sorted by relevance.

6. SEARCH MODE
--------------

To start the console interface, run "python3 search.py".

Then, input each query or type q to quit.

7. EVALUATION MODE
------------------

To run all the queries in TEST.txt, run "python3 search.py --eval".
For each query, the program prints the elapsed query time, the top returned URL, and flags such as NO RESULTS, SLOW< or PARTIAL.

SLOW means the query took longer than 300 ms.
PARTIAL means at least one returned result matched fewer than all query terms.

8. MILESTONE 2 REPORT
---------------------

Print the top five results for the Milestone 2 queries by running "python3 search.py --report".

To save the output to a text file, run "python3 search.py --report > report.txt".

9. TEST.txt FORMAT
-------------------

TEST.txt contains the test queries used to evaluate the search engine.

10. RANKING
-----------

The ranking is based on tf-idf.

tf uses a logarithmic form: 1 + ln(term frequency)
idf uses log(N / df), where N is the number of documents and df is the number of documents containing the terms
terms with important HTML tags receive an additional boost
document norms are applied when available
documents containing all queries are preferred

