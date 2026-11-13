import os, json, heapq, warnings
from collections import defaultdict
from pathlib import Path
from urllib.parse import urldefrag
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning, MarkupResemblesLocatorWarning
from nltk.stem import PorterStemmer
try:
    import lxml
    PARSER = "lxml"
except ImportError:
    PARSER = "html.parser"

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

directory = Path("./DEV/")
PARTIAL_NUM = 5000
stemmer = PorterStemmer()

index = defaultdict(list)
doc_urls = {}
seen_urls = set()
partial_file_paths = []

def tokenize(text):
    """Splits text to lowercase alphanumeric tokens."""
    cleaned = "".join(c if c.isalnum() else " " for c in text)
    return cleaned.lower().split()


def index_document(doc_id, html):
    """Parses one page and adds its terms to the index."""
    soup = BeautifulSoup(html, PARSER)
    important_stems = set()
    important_tags = soup.find_all(['b', 'strong', 'h1', 'h2', 'h3', 'title'])

    for tag in important_tags:
        for token in tokenize(tag.get_text(" ")):
            important_stems.add(stemmer.stem(token))

    tokens = tokenize(soup.get_text(" "))
    term_counts = defaultdict(int)
    for term in tokens:
        stemmed = stemmer.stem(term)
        term_counts[stemmed] += 1

    for term, count in term_counts.items():
        index[term].append((doc_id, count, int(term in important_stems)))


def write_partial():
    """Writes the index to a sorted partial file and frees memory."""
    if not index:
        return
    path = f"partial_{len(partial_file_paths)}.txt"
    with open(path, "w", encoding="utf-8") as file:
        for term in sorted(index):
            postings = ",".join(f"{d}:{c}:{i}" for d, c, i in index[term])
            file.write(f"{term}\t{postings}\n")

    partial_file_paths.append(path)
    index.clear()
    print(f"Wrote {path}")


def read_partial(path):
    """Yields terms and postings from a partial file in a tuple."""
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            term, postings = line.rstrip("\n").split("\t", 1)
            yield term, postings


def merge_partials(final_path="index.txt", offsets_path="offsets.json"):
    """Merges all partial files into a single sorted index file and returns num of unique terms."""
    offsets = {}
    with open(final_path, "wb") as out:
        def write_term(term, posts):
            offsets[term] = out.tell()
            out.write(f"{term}\t{','.join(posts)}\n".encode("utf-8"))

        cur_term, cur_posts = None, []
        streams = [read_partial(p) for p in partial_file_paths]

        for term, posts in heapq.merge(*streams, key=lambda x: x[0]):
            if term != cur_term:
                if cur_term is not None:
                    write_term(cur_term, cur_posts)
                cur_term, cur_posts = term, []
            cur_posts.append(posts)
        
        if cur_term is not None:
            write_term(cur_term, cur_posts)

    with open(offsets_path, "w", encoding="utf-8") as file:
        json.dump(offsets, file)
    for path in partial_file_paths:
        os.remove(path)

    return len(offsets)


def build_index():
    """Read every page, index it, and write partials to disk."""
    doc_id = 0
    for file in sorted(directory.rglob("*.json")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(data, dict):
            continue

        url = urldefrag(data.get("url", ""))[0]
        html = data.get("content", "")
        if not url or not html or url in seen_urls:
            continue

        seen_urls.add(url)
        doc_urls[doc_id] = url
        index_document(doc_id, html)
        doc_id += 1

        if doc_id % PARTIAL_NUM == 0:
            write_partial()

    write_partial() # for leftovers


def report_stats(num_terms, final_path="index.txt"):
    """Prints the numbers for the report."""
    size_kb = os.path.getsize(final_path) / 1024
    print("Indexed documents:", len(doc_urls))
    print("Unique terms:", num_terms)
    print("Index size on disk (KB):", size_kb)


if __name__ == "__main__":
    build_index()
    num_terms = merge_partials()
    with open("docs_urls.json", "w", encoding="utf-8") as file:
        json.dump(doc_urls, file)
    report_stats(num_terms)