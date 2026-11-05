from collections import defaultdict
from pathlib import Path
import json
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress the XML parsed as HTML warning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

documents = {}
directory = Path("./ANALYST/")

index = defaultdict(list)

def get_documents():
    for file in directory.rglob("*.json"):
        with open(file, "r", encoding="utf-8") as f:
            documents[file.stem] = json.load(f)
    print("Documents loaded. Total documents:", len(documents))

def index_documents():
    for doc_id, data in documents.items():
        raw_html = data.get("content", "")

        soup = BeautifulSoup(raw_html, "html.parser")
        text = soup.get_text()

        for term in text.lower().split():
            index[term].append(doc_id)

    print("Indexing complete. Indexed terms:", len(index))

get_documents()
index_documents()
