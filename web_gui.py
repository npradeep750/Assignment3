# Web interface for the search engine (extra credit).
# Run with python3 web_gui.py and then open http://localhost:8000 in a browser
# Or for a different port use python3 web_gui.py 8080 (or another number than 8080)

import html
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from search import Searcher, query_terms

HOST = "127.0.0.1"        # only reachable from this machine (or through a port forward)
PORT = 8000
PAGE_SIZE = 20            # results per page; the "Next 20" button shows the following ones
MAX_START = 1000          # how deep the Next button can go
MAX_QUERY_LENGTH = 200    # longer queries are cut off

# The Searcher keeps one open index file and seeks inside it, so only one request may use it
# at a time. This lock makes the server safe even though it handles requests in threads.
SEARCH_LOCK = threading.Lock()


def results_html(searcher, query, start):
    """Run the query and return the HTML for one page of results."""
    # Ask for one more result than the page needs, so we know whether a "Next" page exists.
    begin = time.perf_counter()
    with SEARCH_LOCK:
        results = searcher.search(query, top_k=start + PAGE_SIZE + 1)
    elapsed_ms = (time.perf_counter() - begin) * 1000

    page = results[start:start + PAGE_SIZE]
    has_next = len(results) > start + PAGE_SIZE
    total = len(query_terms(query))

    if not page:
        message = "No documents found." if start == 0 else "No more results."
        return f"<p>{message} ({elapsed_ms:.1f} ms)</p>"

    lines = [f"<p>Results {start + 1}-{start + len(page)} ({elapsed_ms:.1f} ms)</p>"]
    if results[0][3] < total:    # even the best result lacks some query words
        lines.append("<p>No page contains every word, so these are the closest matches.</p>")

    lines.append(f'<ol start="{start + 1}">')
    for _, url, score, matched in page:
        safe_url = html.escape(url, quote=True)           # URLs come from crawled data: always escape
        if url.startswith(("http://", "https://")):
            link = f'<a href="{safe_url}">{safe_url}</a>'
        else:
            link = safe_url
        note = f" - matches {matched} of {total} words" if matched < total else ""
        lines.append(f"<li>{link}<br>score {score:.3f}{note}</li>")
    lines.append("</ol>")

    if has_next:
        safe_query = html.escape(query, quote=True)
        lines.append('<form method="get" action="/">'
                     f'<input type="hidden" name="q" value="{safe_query}">'
                     f'<input type="hidden" name="start" value="{start + PAGE_SIZE}">'
                     f'<input type="submit" value="Next {PAGE_SIZE}">'
                     "</form>")
    return "\n".join(lines)


def page_html(searcher, query, start):
    """The whole page: title, search box, and the results if there is a query."""
    safe_query = html.escape(query, quote=True)
    body = results_html(searcher, query, start) if query else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><title>ICS Search</title></head>\n'
        "<body>\n"
        "<h1>ICS Search</h1>\n"
        '<form method="get" action="/">'
        f'<input type="text" name="q" value="{safe_query}" size="50" autofocus> '
        '<input type="submit" value="Search">'
        "</form>\n"
        f"{body}\n"
        f"<p>{searcher.num_docs:,} documents indexed</p>\n"
        "</body>\n"
        "</html>\n"
    )


class Handler(BaseHTTPRequestHandler):
    searcher = None    # the shared Searcher, set in main()
    timeout = 10       # drop connections that send nothing for 10 s (browsers open spare idle ones)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/":
            self.send_error(404, "Not found")
            return

        params = parse_qs(parsed.query)
        query = params.get("q", [""])[0].strip()[:MAX_QUERY_LENGTH]
        try:
            start = int(params.get("start", ["0"])[0])
        except ValueError:
            start = 0
        start = max(0, min(start, MAX_START))

        data = page_html(self.searcher, query, start).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python3 web_gui.py [port]   (got {sys.argv[1]!r})", file=sys.stderr)
            return 1

    try:
        searcher = Searcher()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    Handler.searcher = searcher

    # ThreadingHTTPServer handles each connection in its own thread. A single-threaded server
    # can get stuck waiting on a browser's spare idle connection and make pages load slowly.
    try:
        server = ThreadingHTTPServer((HOST, port), Handler)
    except OSError as e:
        print(f"Could not start the server on port {port}: {e}", file=sys.stderr)
        searcher.close()
        return 1

    print(f"Search engine running at http://localhost:{port}  (press Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()
        searcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())