"""One compact, self-contained label layout for browser and native printing."""

LABEL_CSS = '''
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{min-height:100vh;display:flex;flex-direction:column;font:13px system-ui,sans-serif;color:#111;background:#f5f5f5}
.print-toolbar{padding:20px 16px 8px;text-align:center}
.print-toolbar button{padding:12px 20px;font:inherit;cursor:pointer}
.print-toolbar p{margin:10px auto;max-width:560px;font-size:12px;line-height:1.5;color:#555}
.labels{flex:1;display:grid;grid-template-columns:repeat(2,minmax(0,76mm));justify-content:center;align-content:center;gap:6mm;padding:16px 12px;width:100%;margin:0 auto}
.labels.single{grid-template-columns:minmax(0,76mm)}
.qr-label{width:76mm;max-width:100%;height:78mm;padding:4mm;border:1px dashed #aaa;background:white;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:1.4mm;break-inside:avoid;page-break-inside:avoid;overflow:hidden}
.qr-label h2{font-size:10pt;line-height:1.2;margin:0;letter-spacing:.4px}
.qr-label .label-title{font-size:10pt;line-height:1.2;margin:0;max-width:100%;max-height:8.5mm;overflow:hidden;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2}
.qr-label svg{display:block;width:42mm;height:auto;aspect-ratio:1;max-width:100%;flex:none;shape-rendering:crispEdges;background:white}
.qr-label strong{font:700 11pt ui-monospace,Consolas,monospace;line-height:1.3;overflow-wrap:anywhere;max-width:100%}
.qr-label .label-help{font-size:8pt;line-height:1.2;margin:0;color:#333}
@media screen and (max-width:650px){.labels{grid-template-columns:minmax(0,76mm)}}
@page{size:A4 portrait;margin:10mm}
@media print{
 html,body{min-height:0;background:white}
 body{display:block}
 .print-toolbar{display:none}
 .labels{display:grid;grid-template-columns:repeat(2,76mm);justify-content:center;align-content:start;gap:6mm;padding:0;margin:0;width:100%}
 .labels.single{grid-template-columns:76mm;min-height:276mm;align-content:center}
 .qr-label{color:#000;background:#fff;box-shadow:none}
}
'''


def render_labels(cards):
    layout = 'labels single' if len(cards) == 1 else 'labels'
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Thrift for Good labels</title><style>' + LABEL_CSS + '</style></head><body>'
        '<header class="print-toolbar"><button onclick="window.print()">Print labels / Save PDF</button>'
        '<p>Print at actual size (100%) on A4 paper. Cut along the dashed edge. '
        'Each label is 76 × 78 mm with a 42 mm QR code. '
        'Select several records in Inventory to print up to six labels per sheet.</p></header>'
        '<main class="' + layout + '">' + ''.join(cards) + '</main></body></html>'
    )
