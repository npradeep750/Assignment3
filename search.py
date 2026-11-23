import heapq
import json
import math
import sys
import time
from pathlib import Path
from inverter import tokenize, stemmer
from norms import IMPORTANT_BOOST

INDEX_PATH = Path("index.txt")
OFFSET_PATH = Path("offsets.json")
DOCS_PATH = Path("docs_urls.json")
TOP_K = 5
NORMS_PATH = Path("doc_norms.json")
NORMS_POWER = 0.5 # 1 = full cosine length normalization, 0 is none

REPORT_QUERIES = ["cristina lopes", "machine learning", "ACM", "master of software engineering"]
SLOW_MS = 300

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

        self.norms = None
        if NORMS_PATH.exists():
            with open(NORMS_PATH, "r", encoding="utf-8") as file:
                norms = json.load(file)
            if len(norms) == self.num_docs:
                self.norms = [norm ** NORMS_POWER for norm in norms]
            else:
                print(f"{NORMS_PATH} does not match the index (stale?). Run norms.py again.", file=sys.stderr)
        else:
            print(f"{NORMS_PATH} not found, so scores are not length-normalized. Run norms.py to create it.", file=sys.stderr)

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

        flat = postings.replace(":", ",").split(",")
        return dict(zip(map(int, flat[0::3]), zip(map(int, flat[1::3]), map(int, flat[2::3]))))


    def _postings(self, term):
        """Gets the postings from """
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


    def _score(self, doc_id, posting_lists, idfs):
        """Cosine-style tf-idf score of one document, and how many query terms it contains."""
        score = 0.0
        matched = 0
        for postings, idf in zip(posting_lists, idfs):
            entry = postings.get(doc_id)
            if entry is not None:
                tf, important = entry
                score += idf * idf * (1 + math.log(tf)) * (1 + IMPORTANT_BOOST * important)
                matched += 1
        norm = self.norms[doc_id] if self.norms else 1.0
        return score / norm, matched


    def _top(self, doc_ids, posting_lists, idfs, top_k):
        """Best top_k of doc_ids: most query terms matched first, then highest score."""
        scored = []
        for doc_id in doc_ids:
            score, matched = self._score(doc_id, posting_lists, idfs)
            scored.append((-matched, -score, doc_id))
        best = heapq.nsmallest(top_k, scored)
        return [(doc_id, self.docs_urls.get(doc_id, ""), -neg_score, -neg_matched) for neg_matched, neg_score, doc_id in best]


    def search(self, query, top_k=TOP_K):
        """Ranked search. Pages that contain all query terms come first. If there are
        less than top_k of them, then pages matching only some terms fill in the rest.
        Returns [(doc_id, url, score, terms_matched), ...] best first."""
        terms = query_terms(query)
        posting_lists = []
        for term in terms:
            postings = self._postings(term)
            if postings:
                posting_lists.append(postings)
        if not posting_lists:
            return []
        idfs = [math.log(self.num_docs / len(postings)) for postings in posting_lists]            

        results = []
        and_docs = set()
        if len(posting_lists) == len(terms):
            ordered = sorted(posting_lists, key=len)
            and_docs = set(ordered[0])
            for postings in ordered[1:]:
                and_docs.intersection_update(postings)
                if not and_docs:
                    break
            results = self._top(and_docs, posting_lists, idfs, top_k)

        if len(results) < top_k:
            partial_docs = set().union(*posting_lists) - and_docs
            results += self._top(partial_docs, posting_lists, idfs, top_k - len(results))

        return results
    

def print_results(query, results, elapsed_ms):
    total = len(query_terms(query))
    print(f'\nResults for "{query}" (AND, top {TOP_K}, {elapsed_ms:.2f} ms):')
    if not results:
        print("No documents found.")
        return

    for rank, (_, url, score, matched) in enumerate(results, 1):
        note = "" if matched == total else f"   [matches {matched} of {total} terms]"
        print(f"{rank}. {url}    (score {score:.3f}){note}")

def run_query(searcher, query):
    start = time.perf_counter()
    results = searcher.search(query)
    elapsed_ms = (time.perf_counter() - start) * 1000
    print_results(query, results, elapsed_ms)

def run_eval(searcher, path="TEST.txt"):
    """Run every non-commented query in TEST.txt and flag problems."""
    queries = []
    with open(path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)

    for query in queries:
        start = time.perf_counter()
        results = searcher.search(query)
        elapsed_ms = (time.perf_counter() - start) * 1000
        total = len(query_terms(query))
        flags = []
        if not results:
            flags.append("NO RESULTS")
        if elapsed_ms > SLOW_MS:
            flags.append("SLOW")
        if any(result[3] < total for result in results):
            flags.append("PARTIAL")
        flag = "+".join(flags) or "ok"
        top_url = results[0][1] if results else "-"
        print(f"{flag:14} {elapsed_ms:7.1f} ms  {query!r:40} top: {top_url}")

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

        if sys.argv[1:] == ["--eval"]:
            run_eval(searcher)
            return 0
        
        if len(sys.argv) > 1:
            run_query(searcher, " ".join(sys.argv[1:]).strip())
            return 0

        print("Ranked search. Type 'help' for commands, 'quit' to exit.")
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
                print("Enter terms separated by spaces. Results list pages with most matches.")
                continue
            run_query(searcher, query)
    finally:
        searcher.close()

    return 0

if __name__ == "__main__":
    raise SystemExit(main())