"""Regression suite. Run:  python3 tests/regression.py [site_dir]
Serves the site locally, drives headless Chromium (Playwright) and mocks GitHub + Formspree,
so no real form submission or external request is ever made."""
import sys, os, json, threading, http.server, socketserver, re
from playwright.sync_api import sync_playwright
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..'))
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def log_message(s,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(("127.0.0.1",0),Q); PORT=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL=f"http://127.0.0.1:{PORT}/index.html"
results=[]
def check(name,ok,detail=""):
    results.append((name,bool(ok),detail)); print(("PASS " if ok else "FAIL ")+name+(f"  [{detail}]" if detail else ""))

# synthetic payload used ONLY by tests (never shipped)
NOW_ISO=lambda days: __import__('datetime').datetime.utcnow().replace(microsecond=0).__sub__(__import__('datetime').timedelta(days=days)).isoformat()+"Z"
MOCK_USER={"public_repos":20,"followers":7,"following":9}
MOCK_REPOS=[{"name":"tawasol","stargazers_count":2,"language":"TypeScript","fork":False,"pushed_at":NOW_ISO(10)},
            {"name":"Furniture-E-Commerce","stargazers_count":0,"language":"HTML","fork":False,"pushed_at":NOW_ISO(40)},
            {"name":"seif-portfolio","stargazers_count":1,"language":"HTML","fork":False,"pushed_at":NOW_ISO(3)},
            {"name":"mustafa-portfolio","stargazers_count":0,"language":"CSS","fork":False,"pushed_at":NOW_ISO(0)}]
def gh_ok(route):
    u=route.request.url
    body=MOCK_REPOS if "/repos" in u else MOCK_USER
    route.fulfill(status=200,content_type="application/json",body=json.dumps(body))
def gh_403(route): route.fulfill(status=403,content_type="application/json",body='{"message":"API rate limit exceeded"}')
def gh_abort(route): route.abort()

def new_page(b,w=1200,h=800,gh=gh_ok,**ctx):
    c=b.new_context(viewport={"width":w,"height":h},**ctx); p=c.new_page()
    errs=[]; bad=[]
    p.on("console",lambda m: errs.append(m.text) if m.type=="error" else None)
    p.on("pageerror",lambda e: errs.append("PAGEERROR "+str(e)))
    p.on("response",lambda r: bad.append((r.status,r.url)) if r.url.startswith(f"http://127.0.0.1:{PORT}") and r.status>=400 else None)
    p.route("https://api.github.com/**",gh)
    p.route("https://formspree.io/**",lambda r: r.fulfill(status=200,content_type="application/json",body='{"ok":true}'))
    p.goto(URL,wait_until="load"); p.wait_for_timeout(700)
    p._errs=errs; p._bad=bad; return p

with sync_playwright() as pw:
    b=pw.chromium.launch()

    # 1 ── responsive / overflow at the five required widths
    for w,h in [(360,740),(390,844),(768,1024),(1200,800),(1440,900)]:
        p=new_page(b,w,h)
        p.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))")
        m=p.evaluate("""()=>{const de=document.documentElement;window.scrollTo(300,0);
          const f=document.querySelector('.photo-frame').getBoundingClientRect();
          const chips=[...document.querySelectorAll('.photo-chip')].map(c=>{const r=c.getBoundingClientRect();return r.left>=-0.5&&r.right<=de.clientWidth+0.5});
          return {sw:de.scrollWidth,cw:de.clientWidth,sx:window.scrollX,fw:Math.round(f.width),fh:Math.round(f.height),chips,
                  ox:getComputedStyle(de).overflowX+'/'+getComputedStyle(document.body).overflowX}}""")
        check(f"no horizontal overflow @{w}px",m["sw"]<=m["cw"] and m["sx"]==0,f"scrollW={m['sw']} clientW={m['cw']} photo={m['fw']}x{m['fh']} html/body overflow-x={m['ox']}")
        check(f"hero chips inside viewport @{w}px",all(m["chips"]))
        p.screenshot(path=f"/tmp/qa_after_hero_{w}.png")
        check(f"no console errors / 4xx local assets @{w}px",not p._errs and not p._bad,str(p._errs[:2]+p._bad[:2]))
        p.context.close()

    # 2 ── timeAgo (shipped function, executed in the page)
    p=new_page(b)
    cases=[(0,"just now"),(30,"just now"),(120,"2 min ago"),(7200,"2 hr ago"),(86400*1,"1 day ago"),(86400*6,"6 days ago"),
           (86400*7,"1 week ago"),(86400*14,"2 weeks ago"),(86400*29,"4 weeks ago"),(86400*30,"1 month ago"),(86400*31,"1 month ago"),
           (86400*45,"1 month ago"),(86400*90,"2 months ago"),(86400*364,"11 months ago"),(86400*365,"1 year ago"),(86400*800,"2 years ago")]
    bad=[]
    for secs,exp in cases:
        got=p.evaluate("([s])=>timeAgo(new Date(1_700_000_000_000-s*1000),1_700_000_000_000)",[secs])
        if got!=exp: bad.append((secs,exp,got))
    check("timeAgo boundaries (incl. 7–30 days never '0 months')",not bad,str(bad))
    check("timeAgo invalid → ''",p.evaluate("timeAgo('nope')==='' && timeAgo(undefined)==='' && timeAgo(null)===''"))
    check("timeAgo far-future → '', small skew → 'just now'",p.evaluate("timeAgo(new Date(Date.now()+86400000))==='' && timeAgo(new Date(Date.now()+60000))==='just now'"))

    # 3 ── content honesty
    html=open(os.path.join(ROOT,"index.html"),encoding="utf-8").read(); js=open(os.path.join(ROOT,"main.js"),encoding="utf-8").read()
    check("no simulated contribution graph / fallback stats in code",not re.search(r"SIMULATED|contrib-grid|FALLBACK_REPOS|Calculating",html+js))
    check("no unmeasured '70%' claim / 'master' / 'production-quality' / 'intelligent web'",not re.search(r"70%|\bmaster\b|production-quality|intelligent web|AI & Full-Stack",html+js,re.I))
    check("no generic github-profile link used as project source",html.count('href="https://github.com/moustafax7-dotcom"')>0 and not re.search(r'proj-lk"[^>]*href="https://github.com/moustafax7-dotcom"|href="https://github.com/moustafax7-dotcom"[^>]*proj-lk',html))
    check("Furniture card does not claim React",not re.search(r"Furniture E-Commerce.{0,1500}React\.js",html.split("Seif's Portfolio")[0],re.S))
    txt=p.evaluate("""()=>({live:document.querySelector('[data-count=live]').textContent,proj:document.querySelectorAll('[data-count=projects]')[0].textContent,
        tr:document.querySelector('[data-count=trainings]').textContent,cr:document.querySelector('[data-count=credentials]').textContent,
        badges:[...document.querySelectorAll('.feat-proj-badge')].map(e=>e.textContent.trim()),depi:[...document.querySelectorAll('.badge')].filter(e=>/Active Training/.test(e.textContent)).length})""")
    check("counts derived from page (live=2, projects=3, trainings=4, certificates=7)",(txt["live"],txt["proj"],txt["tr"],txt["cr"])==("2","3","4","7"),str(txt))
    check("DEPI no longer 'Active Training'",txt["depi"]==0)

    # 4 ── GitHub behaviour is covered in tests/github.py
    p.context.close()

    # 5 ── mobile navigation
    p=new_page(b,390,844)
    btn=p.locator("#ham"); menu=p.locator("#mob-menu")
    check("menu initially closed, aria-expanded=false",btn.get_attribute("aria-expanded")=="false" and not menu.is_visible())
    btn.click(); check("open: aria-expanded=true, menu visible, label 'Close menu'",btn.get_attribute("aria-expanded")=="true" and menu.is_visible() and btn.get_attribute("aria-label")=="Close menu")
    p.keyboard.press("Escape")
    check("Escape closes menu and returns focus to button",btn.get_attribute("aria-expanded")=="false" and not menu.is_visible() and p.evaluate("document.activeElement.id")=="ham")
    btn.click(); p.locator("#mob-menu a[href='#projects']").click(); p.wait_for_timeout(400)
    check("choosing a link closes the menu and keeps state in sync",btn.get_attribute("aria-expanded")=="false" and not menu.is_visible())
    btn.click(); p.mouse.click(200,700)
    check("clicking outside closes the menu",btn.get_attribute("aria-expanded")=="false")
    p.context.close()

    # 6 ── keyboard / landmarks / labels
    p=new_page(b)
    p.keyboard.press("Tab")
    check("first Tab stop is the skip link",p.evaluate("document.activeElement.className")=="skip-link")
    p.keyboard.press("Enter"); p.wait_for_timeout(200)
    check("skip link moves to <main>",p.evaluate("location.hash")=="#main" and p.evaluate("!!document.querySelector('main#main')"))
    r=p.evaluate("""()=>({h1:document.querySelectorAll('h1').length,labels:[...document.querySelectorAll('#cform input:not([name=_gotcha]),#cform textarea')].every(i=>document.querySelector(`label[for=${i.id}]`)),
        lang:document.documentElement.lang,imgAlt:[...document.images].every(i=>i.hasAttribute('alt')),
        ph:getComputedStyle(document.querySelector('#f-name'),'::placeholder').color,
        blank:[...document.querySelectorAll('a[target=_blank]')].filter(a=>!/noopener/.test(a.rel)).length,
        h:[...document.querySelectorAll('h1,h2,h3')].map(e=>+e.tagName[1])})""")
    seq_ok=all(b2-a2<=1 for a2,b2 in zip(r["h"],r["h"][1:]))
    check("one <h1>, heading levels never skip downward",r["h1"]==1 and seq_ok,str(r["h"]))
    check("all form fields have visible labels; all images have alt",r["labels"] and r["imgAlt"])
    check("placeholder colour is not the old #2a2b38",r["ph"]!="rgb(42, 43, 56)",r["ph"])
    check("all target=_blank links have rel=noopener",r["blank"]==0)
    p.context.close()

    # 7 ── contact form (Formspree mocked — nothing real is sent)
    p=new_page(b,390,844); p.locator("#cform .f-btn").scroll_into_view_if_needed()
    p.click("#cform .f-btn")
    e=p.evaluate("""()=>({inv:[...document.querySelectorAll('#cform [aria-invalid=true]')].map(i=>i.id),errs:[...document.querySelectorAll('.f-err:not([hidden])')].map(x=>x.textContent),
        focus:document.activeElement.id,status:document.getElementById('f-status').textContent})""")
    check("empty submit: 3 inline errors, aria-invalid, focus on first invalid, status message",e["inv"]==["f-name","f-email","f-message"] and len(e["errs"])==3 and e["focus"]=="f-name" and e["status"],str(e))
    p.fill("#f-name","Test"); p.fill("#f-email","not-an-email"); p.fill("#f-message","hi"); p.click("#cform .f-btn")
    check("invalid email gets a specific message",p.inner_text("#f-email-err").startswith("Please enter a valid email"),p.inner_text("#f-email-err"))
    p.fill("#f-email","test@example.com")
    check("error clears as soon as the field is fixed",p.locator("#f-email-err").is_hidden() and p.get_attribute("#f-email","aria-invalid") is None)
    sent=[]
    p.route("https://formspree.io/**",lambda r:(sent.append(r.request.post_data),r.fulfill(status=200,content_type="application/json",body='{"ok":true}')))
    p.click("#cform .f-btn"); p.wait_for_selector(".f-ok")
    check("success: confirmation shown, focus moved to it, payload went only to the mocked endpoint",p.evaluate("document.activeElement.className")=="f-ok" and len(sent)==1 and "test@example.com" in sent[0])
    p.context.close()
    p=new_page(b,390,844)
    p.route("https://formspree.io/**",lambda r: r.fulfill(status=404,content_type="application/json",body='{"error":"Form not found"}'))
    p.fill("#f-name","Test"); p.fill("#f-email","test@example.com"); p.fill("#f-message","Keep this text"); p.click("#cform .f-btn"); p.wait_for_selector(".f-status.is-error")
    check("endpoint failure: clear error + email/WhatsApp fallback, typed message preserved, button re-enabled",
          p.input_value("#f-message")=="Keep this text" and not p.locator("#cform .f-btn").is_disabled() and p.locator(".f-status a").count()==2)
    p.context.close()

    # 8 ── CV, links, loader, anchors
    p=new_page(b)
    href=p.get_attribute("#cvBtn","href"); r=p.request.get(f"http://127.0.0.1:{PORT}/{href}")
    check("CV is a direct PDF link that returns a real PDF",r.status==200 and r.body()[:5]==b"%PDF-" and p.get_attribute("#cvBtn","download"),f"{href} {len(r.body())} bytes")
    ids=p.evaluate("[...document.querySelectorAll('a[href^=\"#\"]')].map(a=>a.getAttribute('href').slice(1)).filter(x=>x&&!document.getElementById(x))")
    check("every in-page anchor has a target",ids==[],str(ids))
    check("loader removed without waiting for load + 800ms",p.evaluate("!document.getElementById('loader')"))
    pre=p.evaluate("document.documentElement.classList.contains('has-cursor')")
    p.mouse.move(300,300); p.mouse.move(340,320); p.wait_for_timeout(200)
    post=p.evaluate("({on:document.documentElement.classList.contains('has-cursor'),fine:matchMedia('(hover: hover) and (pointer: fine)').matches,ring:getComputedStyle(document.getElementById('cur-r')).display})")
    check("custom cursor is not set up at startup; it activates on the first real mouse move (fine pointer only); skip link off-screen",
          (not pre) and post['on']==post['fine'] and (post['ring']=="block")==post['fine'] and p.evaluate("document.querySelector('.skip-link').getBoundingClientRect().bottom<=0"),str((pre,post)))
    p.context.close()
    p=new_page(b,390,844,has_touch=True,is_mobile=True)
    check("touch device keeps native cursor, custom cursor hidden",p.evaluate("!document.documentElement.classList.contains('has-cursor') && getComputedStyle(document.getElementById('cur-r')).display")=="none")
    t=p.evaluate("""()=>[...document.querySelectorAll('a,button,input,textarea')].filter(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);return r.width>0&&cs.visibility!=='hidden'&&!e.closest('.f-hp,.skip-link,.sec-sub')&&(r.width<24||r.height<24)}).map(e=>(e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().width)+'x'+Math.round(e.getBoundingClientRect().height))""")
    check("touch targets ≥24×24 CSS px (WCAG 2.5.8) @390px",t==[],str(t[:6]))
    p.context.close()

    # 9 ── reduced motion
    p=new_page(b,1200,800,reduced_motion="reduce")
    r=p.evaluate("""()=>({typed:document.getElementById('typed').textContent,rev:[...document.querySelectorAll('.reveal')].every(e=>e.classList.contains('in')),
        cursor:document.documentElement.classList.contains('has-cursor'),anim:getComputedStyle(document.querySelector('.photo-ring')).animationName})""")
    p.wait_for_timeout(3500)
    typed_after=p.evaluate("document.getElementById('typed').textContent")
    check("prefers-reduced-motion: static title, reveals visible, no custom cursor, ring animation off",r["typed"]=="Frontend Developer | React.js" and typed_after==r["typed"] and r["rev"] and not r["cursor"] and r["anim"]=="none",str(r))
    p.context.close()

    # 10 ── SEO
    p=new_page(b)
    s=p.evaluate("""()=>({t:document.title,c:document.querySelector('link[rel=canonical]').href,ou:document.querySelector('meta[property="og:url"]').content,
        oi:document.querySelector('meta[property="og:image"]').content,tc:document.querySelector('meta[name="twitter:card"]').content,
        d:document.querySelector('meta[name=description]').content.length,ld:JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent)['@type']})""")
    P="https://mustafa-portfolio-lyart.vercel.app/"
    check("canonical, og:url and og:image all use the Vercel domain",s["c"]==P and s["ou"]==P and s["oi"].startswith(P) and "github.io" not in html.split("</head>")[0])
    check("og:image file exists at 1200×630",os.path.exists(os.path.join(ROOT,"assets/og-image.png")) and __import__('PIL.Image',fromlist=['x']).open(os.path.join(ROOT,"assets/og-image.png")).size==(1200,630))
    check("title/description/JSON-LD present and valid JSON",s["t"].startswith("Mustafa Mahmoud") and 70<s["d"]<=170 and s["ld"]=="ProfilePage" and s["tc"]=="summary_large_image",str(s))
    check("robots.txt and sitemap.xml exist",os.path.exists(os.path.join(ROOT,"robots.txt")) and os.path.exists(os.path.join(ROOT,"sitemap.xml")))
    p.context.close(); b.close()

fails=[r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} checks passed"); sys.exit(1 if fails else 0)
