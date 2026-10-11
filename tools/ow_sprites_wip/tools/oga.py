import re, html, sys, subprocess
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
def get(url):
    return subprocess.run(['curl', '-sL', '-A', UA, url], capture_output=True).stdout.decode('utf-8', 'ignore')
def page(slug):
    h = get('https://opengameart.org/content/' + slug)
    title = re.search(r'<title>(.*?)</title>', h, re.S).group(1)
    author = re.findall(r'<div class="field field-name-author-submitter.*?<a href="/users/[^"]+"[^>]*>([^<]+)</a>', h, re.S)
    lic = re.findall(r'''<div class=['"]license-name['"]>([^<]+)</div>''', h)
    files = [f for f in re.findall(r'href="(https://opengameart.org/sites/default/files/[^"]+)"', h) if '/css/' not in f]
    body = re.search(r'<div class="field field-name-body.*?<div class="field-items">(.*?)</div></div></div>', h, re.S)
    btxt = html.unescape(re.sub(r'<[^>]+>', ' ', body.group(1))) if body else ''
    attr = re.search(r'field-name-field-copyright-notice.*?<div class="field-item even">(.*?)</div>', h, re.S)
    atxt = html.unescape(re.sub(r'<[^>]+>', ' ', attr.group(1))) if attr else ''
    return dict(title=html.unescape(title), author=author[:2], lic=lic, files=sorted(set(files)), body=' '.join(btxt.split())[:700], attribution=' '.join(atxt.split())[:300])
if __name__ == '__main__':
    for s in sys.argv[1:]:
        d = page(s)
        print('=====', s); [print(' ', k, ':', v) for k, v in d.items()]
