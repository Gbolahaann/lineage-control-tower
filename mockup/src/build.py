"""Assemble the HTML mockup into one self-contained file.
Usage: python mockup/src/build.py mockup/src mockup/data/lct_agg.json mockup/lineage-control-tower.html
"""
import sys
d=sys.argv[1]; data=open(sys.argv[2]).read(); out=sys.argv[3]
shell=open(f'{d}/shell.html').read().replace('</style>', open(f'{d}/components.css').read()+'\n</style>')
js='\n'.join(open(f'{d}/{f}').read() for f in ['core.js','views-a.js','views-b.js','views-c.js','boot.js'])
assert '</script' not in data
html = shell + open(f'{d}/body.html').read() + '<script type="application/json" id="lct-data">' + data + '</script>\n<script>\n' + js + '\n</script>\n'
open(out,'w').write(html); print(len(html))
