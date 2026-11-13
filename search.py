import json
import math
import sys
from pathlib import Path
from inverter import tokenize, stemmer

INDEX_PATH = Path("index.txt")
OFFSET_PATH = Path("offsets.json")
DOCS_PATH = Path("docs_urls.json")
TOP_K = 5

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
        self.index_file = open(INDEX_PATH, "rb")

    def close(self):
        self.index_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @staticmethod
    def _parse_doc_ids(postings):
        if isinstance(postings, bytes):
            postings = postings.decode("utf-8")
        doc_ids = []
        for posting in postings.split(","):
            parts = posting.split(":")
            if len(parts) != 3:
                continue
            doc_ids.append(int(parts[0]))
        return doc_ids

    def _postings(self, term):
        offset = self.offsets.get(term)
        if offset is None:
            return []
        self.index_file.seek(offset)
        line = self.index_file.readline()
        if not line:
            return []
        try:
            _, postings = line.rstrip(b"\n").split(b"\t", 1)
        except ValueError:
            return []
        return self._parse_doc_ids(postings)

    def search(self, query, top_k=TOP_K):
        terms = query_terms(query)
        if not terms:
            return []

        posting_lists = []
        for term in terms:
            doc_ids = self._postings(term)
            if not doc_ids:
                return []
            posting_lists.append(set(doc_ids))

        candidates = set(posting_lists[0])
        for doc_ids in posting_lists[1:]:
            candidates.intersection_update(doc_ids)
            if not candidates:
                return []

        results = [
            (doc_id, self.docs_urls.get(doc_id, ""))
            for doc_id in sorted(candidates)
        ]
        return results[:top_k]

def print_results(query, results):
    print(f'\nResults for {query}" (AND, top {TOP_K} URLs):')
    if not results:
        print("No documents found.")
        return

    for rank, (_, url) in enumerate(results, 1):
        print(f"{rank}. {url}")

def main():
    try:
        searcher = Searcher()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1

    try:
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:]).strip()
            print_results(query, searcher.search(query))
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
            print_results(query, searcher.search(query))
    finally:
        searcher.close()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())