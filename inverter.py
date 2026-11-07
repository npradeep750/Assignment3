from collections import defaultdict
from pathlib import Path
import json
import warnings
from bs4 import BeautifulSoup
try:
    from bs4 import XMLParsedAsHTMLWarning
except ImportError:
    XMLParsedAsHTMLWarning = None
from nltk.stem import PorterStemmer

# Suppress the XML parsed as HTML warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

documents = {}
directory = Path("./DEV/")
index = defaultdict(list)
stemmer = PorterStemmer()

def tokenize(text):
    cleaned = "".join(c if c.isalnum() else " " for c in text)
    return cleaned.lower().split()


def get_documents():
    for file in directory.rglob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            try:
                documents[file.stem] = json.load(f)
            except json.JSONDecodeError as e:
                continue
    print("Documents loaded. Total documents:", len(documents))

def index_documents():
    for doc_id, data in documents.items():
        raw_html = data.get("content", "")
        soup = BeautifulSoup(raw_html, "html.parser")

        important_stems = set()
        important_tags = soup.find_all(['b', 'strong', 'h1', 'h2', 'h3', 'title'])
        for tag in important_tags:
            tag_tokens = tokenize(tag.get_text())
            for t in tag_tokens:
                important_stems.add(stemmer.stem(t))

        text = soup.get_text()
        tokens = tokenize(text)

        term_counts = defaultdict(int)
        for term in tokens:
            stemmed = stemmer.stem(term)
            term_counts[stemmed] += 1

        for term, count in term_counts.items():
            index[term].append({"doc_id": doc_id, "count": count, "is_important": term in important_stems})

    print("Indexing complete. Indexed terms:", len(index))

get_documents()
index_documents()