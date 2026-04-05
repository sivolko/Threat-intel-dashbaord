#!/usr/bin/env python3
"""
Convert README.md -> README.html -> README.pdf
Uses: markdown (pip), Microsoft Edge headless

Run: py generate_pdf.py
"""

import subprocess, sys, re, time
from pathlib import Path

ROOT = Path(__file__).parent
MD_FILE   = ROOT / 'README.md'
HTML_FILE = ROOT / 'README.html'
PDF_FILE  = ROOT / 'README.pdf'

EDGE_PATH = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'

# ── Markdown to HTML ──────────────────────────────────────────────────────────
try:
    import markdown
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
except ImportError:
    sys.exit('Run:  py -m pip install markdown')

md_text = MD_FILE.read_text('utf-8')

# Convert to HTML with extensions
html_body = markdown.markdown(
    md_text,
    extensions=['tables', 'fenced_code', 'toc', 'nl2br']
)

# Replace mermaid code blocks with proper mermaid divs so mermaid.js can render them
html_body = re.sub(
    r'<code class="language-mermaid">(.*?)</code>',
    lambda m: f'<div class="mermaid">{m.group(1)}</div>',
    html_body,
    flags=re.DOTALL
)

# ── Full HTML page with styling ───────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Threat Intel Dashboard — README</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13.5px;
    line-height: 1.7;
    color: #1e293b;
    background: #fff;
    padding: 48px 64px;
    max-width: 960px;
    margin: 0 auto;
  }}

  /* Cover banner */
  .cover {{
    background: linear-gradient(135deg, #0f172a 0%, #1e40af 100%);
    color: #fff;
    padding: 36px 40px;
    border-radius: 16px;
    margin-bottom: 40px;
  }}
  .cover h1 {{ font-size: 26px; font-weight: 800; margin-bottom: 6px; }}
  .cover p  {{ font-size: 13px; color: #93c5fd; margin: 0; }}

  h1 {{ font-size: 22px; font-weight: 800; color: #0f172a; margin: 32px 0 12px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }}
  h2 {{ font-size: 18px; font-weight: 700; color: #1e293b; margin: 28px 0 10px; }}
  h3 {{ font-size: 14px; font-weight: 700; color: #334155; margin: 22px 0 8px; text-transform: uppercase; letter-spacing: 0.4px; }}
  h4 {{ font-size: 13px; font-weight: 600; color: #475569; margin: 16px 0 6px; }}

  p  {{ margin: 0 0 12px; color: #374151; }}
  ul, ol {{ padding-left: 20px; margin: 0 0 12px; }}
  li {{ margin-bottom: 4px; color: #374151; }}

  a  {{ color: #2563eb; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  strong {{ font-weight: 700; color: #111827; }}
  em     {{ color: #6b7280; }}
  hr     {{ border: none; border-top: 1px solid #e2e8f0; margin: 28px 0; }}

  /* Inline code */
  code {{
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    background: #f1f5f9;
    color: #1e40af;
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid #e2e8f0;
  }}

  /* Code blocks */
  pre {{
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 10px;
    padding: 18px 20px;
    margin: 12px 0 20px;
    overflow-x: auto;
    font-size: 11.5px;
    line-height: 1.6;
    border: 1px solid #1e293b;
  }}
  pre code {{
    background: transparent;
    color: #e2e8f0;
    padding: 0;
    border: none;
    font-size: inherit;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 20px;
    font-size: 12.5px;
  }}
  thead tr {{ background: #f8fafc; }}
  th {{
    padding: 9px 12px;
    text-align: left;
    font-weight: 700;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #64748b;
    border-bottom: 2px solid #e2e8f0;
  }}
  td {{
    padding: 8px 12px;
    border-bottom: 1px solid #f1f5f9;
    color: #374151;
    vertical-align: top;
  }}
  tr:hover td {{ background: #f8fafc; }}

  /* Mermaid diagrams */
  .mermaid {{
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px;
    margin: 16px 0 24px;
    text-align: center;
    overflow: hidden;
  }}

  /* Blockquote */
  blockquote {{
    border-left: 4px solid #3b82f6;
    background: #eff6ff;
    padding: 10px 16px;
    border-radius: 0 8px 8px 0;
    margin: 12px 0;
    color: #1e40af;
    font-size: 13px;
  }}

  /* Page breaks for PDF */
  h2 {{ page-break-before: auto; }}
  pre, table, .mermaid {{ page-break-inside: avoid; }}

  @media print {{
    body {{ padding: 24px 32px; font-size: 12px; }}
    .cover {{ padding: 24px 28px; }}
    pre {{ font-size: 10.5px; }}
  }}
</style>
</head>
<body>

<div class="cover">
  <h1>🛡️ Threat Intel Dashboard</h1>
  <p>Architecture · Usage · Deployment Guide &nbsp;·&nbsp; Generated {time.strftime('%d %B %Y')}</p>
</div>

{html_body}

<script>
  mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
</script>
</body>
</html>
"""

HTML_FILE.write_text(html, 'utf-8')
print(f'✅  HTML written → {HTML_FILE}')

# ── Edge headless → PDF ───────────────────────────────────────────────────────
print('⏳  Launching Edge headless (waiting for Mermaid render)...')

cmd = [
    EDGE_PATH,
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--run-all-compositor-stages-before-draw',
    '--virtual-time-budget=6000',    # wait 6s for mermaid.js to render
    f'--print-to-pdf={PDF_FILE}',
    '--print-to-pdf-no-header',
    HTML_FILE.as_uri(),
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

if PDF_FILE.exists() and PDF_FILE.stat().st_size > 1000:
    size_kb = PDF_FILE.stat().st_size // 1024
    print(f'✅  PDF written  → {PDF_FILE}  ({size_kb} KB)')
    # Clean up temp HTML
    HTML_FILE.unlink(missing_ok=True)
    print('🗑️   Temp HTML removed')
else:
    print(f'⚠️  PDF may be incomplete. Edge stderr:\n{result.stderr}')
    print(f'    HTML preserved at: {HTML_FILE}')
