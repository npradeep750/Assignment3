from pathlib import Path

from search import Searcher

QUERIES = [
    "cristina lopes",
    "machine learning",
    "ACM",
    "master of software engineering",
]
REPORT_PATH = Path("report.txt")

def main():
    searcher = Searcher()
    lines = []

    try:
        for query in QUERIES:
            lines.append(query)
            results = searcher.search(query)
            
            if results:
                for rank, (_, url) in enumerate(results, 1):
                    lines.append(f"{rank}. {url}")
            else:
                lines.append("No documents found.")

            lines.append("")
    finally:
        searcher.close()

    REPORT_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Report written to {REPORT_PATH.resolve()}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())