import heapq
import json
import math
import sys
import time
from pathlib import Path
from inverter import tokenize, stemmer

INDEX_PATH = Path("index.txt")
OFFSET_PATH = Path("offsets.json")
DOCS_PATH = Path("docs_urls.json")
TOP_K = 5
IMPORTANT_BOOST = 0.5 # for titles/headings to make them more important than body text

REPORT_QUERIES = ["cristina lopes", "machine learning", "ACM", "master of software engineering"]


def query_terms(query):
    terms = []
    seen = set()
    for token in tokenize(query):
        stem = stemmer.stem(token)
        if stem and stem not in seen:
            seen.add(stem)
            terms.append(stem)
    return terms

class Searcher:
    def __init__(self):
        for path in (INDEX_PATH, OFFSET_PATH, DOCS_PATH):
            if not path.exists():
                raise FileNotFoundError(f"{path} does not exist. Please run inverter.py first.")
        with open(OFFSET_PATH, "r", encoding="utf-8") as file:
            self.offsets = json.load(file)

        with open(DOCS_PATH, "r", encoding="utf-8") as file:
            raw_urls = json.load(file)

        self.docs_urls = {int(doc_id): url for doc_id, url in raw_urls.items()}
        self.num_docs = len(self.docs_urls)
        self.index_file = open(INDEX_PATH, "rb")

    def close(self):
        self.index_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @staticmethod
    def _parse_postings(postings):
        """Parse 'doc:tf:important, doc:tf:important, ...' into {doc_id: (tf, important), ...}."""
        if isinstance(postings, bytes):
            postings = postings.decode("utf-8")
        parsed = {}
        for posting in postings.split(","):
            parts = posting.split(":")
            if len(parts) != 3:
                continue
            parsed[int(parts[0])] = (int(parts[1]), bool(int(parts[2])))
        return parsed

    def _postings(self, term):
        offset = self.offsets.get(term)
        if offset is None:
            return {}
        self.index_file.seek(offset)
        line = self.index_file.readline()
        if not line:
            return {}
        try:
            _, postings = line.rstrip(b"\n").split(b"\t", 1)
        except ValueError:
            return {}
        return self._parse_postings(postings)

    def search(self, query, top_k=TOP_K):
        """AND search. Returns parsed postings for documents, ordered by relevance."""
        terms = query_terms(query)
        if not terms:
            return []

        posting_lists = []
        for term in terms:
            postings = self._postings(term)
            if not postings:
                return []
            posting_lists.append(postings)

        posting_lists.sort(key=len)
        candidates = set(posting_lists[0])
        for postings in posting_lists[1:]:
            candidates.intersection_update(postings)
            if not candidates:
                return []

        idfs = [math.log(self.num_docs / len(postings)) for postings in posting_lists]
        scored = []
        for doc_id in candidates:
            score = 0.0
            for postings, idf in zip(posting_lists, idfs):
                tf, important = postings[doc_id]
                score += (1 + math.log(tf)) * idf * (1 + IMPORTANT_BOOST * important)
            scored.append((score, doc_id))

        best = heapq.nsmallest(top_k, scored, key=lambda x: (-x[0], x[1]))
        return [(doc_id, self.docs_urls.get(doc_id, ""), score) for score, doc_id in best]

def print_results(query, results, elapsed_ms):
    print(f'\nResults for "{query}" (AND, top {TOP_K}, {elapsed_ms:.2f} ms):')
    if not results:
        print("No documents found.")
        return

    for rank, (_, url, score) in enumerate(results, 1):
        print(f"{rank}. {url}    (score {score:.3f})")

def run_query(searcher, query):
    start = time.perf_counter()
    results = searcher.search(query)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print_results(query, results, elapsed_ms)

def main():
    try:
        searcher = Searcher()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    try:
        if sys.argv[1:] == ["--report"]:
            for query in REPORT_QUERIES:
                run_query(searcher, query)
            return 0
        
        if len(sys.argv) > 1:
            run_query(searcher, " ".join(sys.argv[1:]).strip())
            return 0

        print("Boolean AND search. Type 'help' for commands, 'quit' to exit.")
        while True:
            try:
                query = input("Search> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not query:
                continue
            if query.lower() in {"quit", "exit", "q"}:
                break
            if query.lower() in {"help", "?"}:
                print("Enter terms separated by spaces to search for documents containing all of them.")
                continue
            run_query(searcher, query)
    finally:
        searcher.close()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())