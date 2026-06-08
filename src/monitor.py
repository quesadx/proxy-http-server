"""Flask monitoring dashboard — real-time proxy metrics on port 8081."""

import threading

from flask import Flask, jsonify

from src.stats import proxy_stats


def create_dashboard(stats=proxy_stats, host="localhost", port=8081):
    """Create and return a Flask app wired to shared stats."""
    app = Flask(__name__)

    @app.route("/")
    def index():
        snapshot = stats.get_snapshot()
        top_domains_rows = "".join(
            f"<tr><td>{d}</td><td>{c}</td></tr>"
            for d, c in snapshot["top_domains"]
        )
        status_rows = "".join(
            f"<tr><td>{s}</td><td>{n}</td></tr>"
            for s, n in snapshot["status_codes"].items()
        )
        return f"""<!DOCTYPE html>
<html lang='es'>
<head><meta charset='utf-8'>
<meta http-equiv='refresh' content='5'>
<title>Proxy Monitor</title>
<style>
  body {{ font-family: monospace; margin: 2em; }}
  .stat {{ margin: 0.5em 0; font-size: 1.1em; }}
  .value {{ font-weight: bold; color: #0066cc; }}
  .blocked {{ color: #cc0000; }}
  table {{ border-collapse: collapse; margin: 1em 0; }}
  td, th {{ border: 1px solid #ccc; padding: 0.3em 0.8em; text-align: left; }}
  th {{ background: #f0f0f0; }}
</style></head>
<body>
<h1>Proxy Monitor</h1>
<h2>Phase 3 — EIF208 UNA</h2>
<p class='stat'>Total: <span class='value'>{snapshot['total_requests']}</span></p>
<p class='stat'>Blocked: <span class='value blocked'>{snapshot['blocked_requests']}</span></p>
<p class='stat'>Allowed: <span class='value'>{snapshot['allowed_requests']}</span></p>
<p class='stat'>Active connections: <span class='value'>{snapshot['active_connections']}</span></p>
<h3>Top 5 domains</h3>
<table><tr><th>Domain</th><th>Requests</th></tr>
{top_domains_rows}
</table>
<h3>Status codes</h3>
<table><tr><th>Status</th><th>Count</th></tr>
{status_rows}
</table>
<h3>Cache</h3>
<p class='stat'>Hits: <span class='value'>{snapshot['cache_hits']}</span></p>
<p class='stat'>Misses: <span class='value'>{snapshot['cache_misses']}</span></p>
<p class='stat'>Hit rate: <span class='value'>{snapshot['hit_rate']}%</span></p>
<hr>
<footer>Proxy Monitor — EIF208 UNA</footer>
</body></html>"""

    @app.route("/api/stats")
    def api_stats():
        return jsonify(stats.get_snapshot())

    return app


def start_dashboard(stats=proxy_stats, host="localhost", port=8081):
    """Start Flask in a daemon thread."""
    app = create_dashboard(stats, host, port)
    thread = threading.Thread(
        target=app.run,
        kwargs={"host": host, "port": port, "debug": False, "use_reloader": False},
        daemon=True,
    )
    thread.start()
    return thread
