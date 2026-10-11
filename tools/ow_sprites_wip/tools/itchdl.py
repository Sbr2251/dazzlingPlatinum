"""Download free itch.io uploads through one proxy tunnel (view_game route)."""
import http.client, json, re, sys, urllib.parse, subprocess, os

UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'


def fetch(page_url, out_dir, want=None):
    u = urllib.parse.urlparse(page_url)
    c = http.client.HTTPSConnection('fwdproxy', 8080, timeout=60)
    c.set_tunnel(u.netloc, 443)
    ck = {}

    def req(m, p, b=None):
        h = {'User-Agent': UA, 'Accept': '*/*'}
        if ck:
            h['Cookie'] = '; '.join(f'{k}={v}' for k, v in ck.items())
        if b is not None:
            h['Content-Type'] = 'application/x-www-form-urlencoded'
            h['X-Requested-With'] = 'XMLHttpRequest'
        c.request(m, p, body=b, headers=h)
        r = c.getresponse()
        d = r.read().decode('utf-8', 'ignore')
        for k, v in r.getheaders():
            if k.lower() == 'set-cookie':
                a, _, bb = v.split(';', 1)[0].partition('=')
                ck[a] = bb
        return d

    page = req('GET', u.path)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    ids = re.findall(r'data-upload_id="(\d+)"', page)
    names = re.findall(r'class="upload_name"><strong title="([^"]+)"', page)
    key = None
    if not ids:
        j = req('POST', u.path.rstrip('/') + '/download_url', urllib.parse.urlencode({'csrf_token': csrf}))
        durl = json.loads(j)['url']
        dpath = urllib.parse.urlparse(durl).path
        dpage = req('GET', dpath)
        key = urllib.parse.unquote(dpath.split('/download/')[1])
        m = re.search(r'name="csrf_token" value="([^"]+)"', dpage)
        csrf = m.group(1) if m else csrf
        ids = re.findall(r'data-upload_id="(\d+)"', dpage)
        names = re.findall(r'class="upload_name"><strong title="([^"]+)"', dpage)
    print('uploads:', list(zip(ids, names)))
    got = []
    for uid, name in zip(ids, names):
        if want and not re.search(want, name, re.I):
            continue
        q = f'source=game_download&key={urllib.parse.quote(key, safe="")}&as_props=1' if key else 'source=view_game&as_props=1&after_download_lightbox=true'
        j = req('POST', f'{u.path.rstrip("/")}/file/{uid}?{q}',
                urllib.parse.urlencode({'csrf_token': csrf}))
        try:
            furl = json.loads(j)['url']
        except Exception:
            print('fail', uid, name, j[:150])
            continue
        dest = os.path.join(out_dir, name.replace('/', '_'))
        subprocess.run(['curl', '-sL', '-A', UA, furl, '-o', dest])
        got.append(dest)
        print('saved', dest, os.path.getsize(dest))
    return got


if __name__ == '__main__':
    os.makedirs(sys.argv[2], exist_ok=True)
    fetch(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
