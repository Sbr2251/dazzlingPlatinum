import re, html, sys, subprocess
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'
for url in sys.argv[1:]:
    h = subprocess.run(['curl', '-sL', '-A', UA, url], capture_output=True).stdout.decode('utf-8', 'ignore')
    m = re.search(r'<div class="formatted_description user_formatted">(.*?)</div>\s*<div class="more_information_toggle', h, re.S) or re.search(r'<div class="formatted_description user_formatted">(.*?)</div>', h, re.S)
    t = html.unescape(re.sub(r'<[^>]+>', '\n', m.group(1))) if m else ''
    t = re.sub(r'\n\s*\n+', '\n', t)
    info = dict((k, re.sub(r'<[^>]+>', '', v)) for k, v in re.findall(r'<tr><td>([^<]+)</td><td>(.*?)</td></tr>', h))
    price = re.search(r'class="buy_message".*?</div>', h, re.S)
    print('=====', url, '| author:', info.get('Author'), '| price:', ' '.join(re.sub(r'<[^>]+>', ' ', price.group(0)).split())[:80] if price else '?')
    print(t[:1800])
    print('imgs:', sorted(set(re.findall(r'https://img.itch.zone/[^" ]*/original/[^" ]*', h)))[:8])
