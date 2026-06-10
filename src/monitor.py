"""Flask monitoring dashboard — real-time proxy metrics on port 8081."""

import threading

from flask import Flask, jsonify, Response

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
        client_rows = "".join(
            f"<tr><td>{ip}</td><td>{count}</td></tr>"
            for ip, count in snapshot["clients"].items()
        )
        data_mb = round(snapshot["bytes_transferred"] / (1024 * 1024), 2)
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
  .allowed {{ color: #009900; }}
  table {{ border-collapse: collapse; margin: 1em 0; }}
  td, th {{ border: 1px solid #ccc; padding: 0.3em 0.8em; text-align: left; }}
  th {{ background: #f0f0f0; }}
  .section {{ margin-top: 1.5em; }}
</style></head>
<body>
<h1>Proxy Monitor</h1>
<h2>EIF208 — Redes, Universidad Nacional (UNA)</h2>
<div class='section'>
<h3>Resumen</h3>
<p class='stat'>Total de solicitudes: <span class='value'>{snapshot['total_requests']}</span></p>
<p class='stat'>Permitidas: <span class='value allowed'>{snapshot['allowed_requests']}</span> ({snapshot['allowed_pct']}%)</p>
<p class='stat'>Bloqueadas: <span class='value blocked'>{snapshot['blocked_requests']}</span> ({snapshot['blocked_pct']}%)</p>
<p class='stat'>Volumen de datos: <span class='value'>{data_mb} MB</span></p>
<p class='stat'>Conexiones activas: <span class='value'>{snapshot['active_connections']}</span></p>
</div>
<div class='section'>
<h3>Clientes activos</h3>
<table><tr><th>IP</th><th>Solicitudes</th></tr>
{client_rows if client_rows else '<tr><td colspan="2">Sin datos</td></tr>'}
</table>
</div>
<div class='section'>
<h3>Top 5 dominios</h3>
<table><tr><th>Dominio</th><th>Solicitudes</th></tr>
{top_domains_rows if top_domains_rows else '<tr><td colspan="2">Sin datos</td></tr>'}
</table>
</div>
<div class='section'>
<h3>Códigos de estado</h3>
<table><tr><th>Código</th><th>Conteo</th></tr>
{status_rows if status_rows else '<tr><td colspan="2">Sin datos</td></tr>'}
</table>
</div>
<div class='section'>
<h3>Cache</h3>
<p class='stat'>Hits: <span class='value'>{snapshot['cache_hits']}</span></p>
<p class='stat'>Misses: <span class='value'>{snapshot['cache_misses']}</span></p>
<p class='stat'>Hit rate: <span class='value'>{snapshot['hit_rate']}%</span></p>
</div>
<hr>
<footer>Proxy Monitor — EIF208 UNA &mdash; <a href='/api/stats'>API JSON</a> | <a href='/api/report'>Exportar CSV</a></footer>
</body></html>"""

    @app.route("/api/stats")
    def api_stats():
        return jsonify(stats.get_snapshot())

    @app.route("/api/report")
    def api_report():
        snapshot = stats.get_snapshot()
        data_mb = round(snapshot["bytes_transferred"] / (1024 * 1024), 2)
        lines = [
            "metrico,valor",
            f"total_requests,{snapshot['total_requests']}",
            f"allowed,{snapshot['allowed_requests']}",
            f"blocked,{snapshot['blocked_requests']}",
            f"blocked_pct,{snapshot['blocked_pct']}",
            f"allowed_pct,{snapshot['allowed_pct']}",
            f"bytes_transferred,{snapshot['bytes_transferred']}",
            f"data_volume_mb,{data_mb}",
            f"active_connections,{snapshot['active_connections']}",
            f"cache_hits,{snapshot['cache_hits']}",
            f"cache_misses,{snapshot['cache_misses']}",
            f"hit_rate,{snapshot['hit_rate']}",
        ]
        for dom, count in snapshot["top_domains"]:
            lines.append(f"top_domain,{dom},{count}")
        for ip, count in snapshot["clients"].items():
            lines.append(f"client,{ip},{count}")
        csv = "\n".join(lines) + "\n"
        return Response(csv, mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=proxy-report.csv"})

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
