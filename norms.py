# Run once after inverter.py builds an index to normalize it into doc_norms.json. Use python3 norms.py to run.

import json
import math
import time

IMPORTANT_BOOST = 0.5 # for titles/headings to make them more important than body text

def doc_weight(tf, important, idf):
    """Returns tf-idf weight of one term in one document (log-scaled tf, boosted if important)."""
    return (1 + math.log(tf)) * idf * (1 + IMPORTANT_BOOST * important)

def build_norms(index_path="index.txt", docs_path="docs_urls.json", out_path="doc_norms.json"):
    """Stream index.txt line by line and write into doc_norms.json."""
    with open(docs_path, "r", encoding="utf-8") as file:
        num_docs = len(json.load(file))

    squared = [0.0] * num_docs

    with open(index_path, "r", encoding="utf-8") as file:
        for line in file:
            _, postings = line.rstrip("\n").split("\t", 1)
            entries = postings.split(",")
            idf = math.log(num_docs / len(entries))
            if idf <= 0:
                continue
            for entry in entries:
                doc_id, tf, important = entry.split(":")
                weight = doc_weight(int(tf), int(important), idf)
                squared[int(doc_id)] += weight * weight

    norms = [math.sqrt(total) or 1.0 for total in squared]
    with open(out_path, "w", encoding="utf-8") as file:
        json.dump(norms, file)
    return num_docs

if __name__ == "__main__":
    start = time.perf_counter()
    count = build_norms()
    print(f"Wrote doc_norms.json for {count} documents in {time.perf_counter() - start:.1f} seconds.")