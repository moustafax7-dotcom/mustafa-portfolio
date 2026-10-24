"""Feature tests: certificates gallery + viewer, Playground (Sushi Bounce only, Bug Hunter removed), projects, responsive, cleanup.
Run: python3 tests/features.py [site_dir]   (nothing real is sent; GitHub/Formspree are mocked)"""
import sys, os, re, threading, http.server, socketserver, json
from playwright.sync_api import sync_playwright
from _launch import launch_kwargs
ROOT=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),'..'))
SHOTS=os.environ.get('SHOTS_DIR') or os.path.join(ROOT,'docs','screenshots'); os.makedirs(SHOTS,exist_ok=True)
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

def page(b,w=1200,h=800,touch=False,**kw):
    c=b.new_context(viewport={"width":w,"height":h},has_touch=touch,is_mobile=touch,**kw); p=c.new_page()
    p._errs=[]; p._reqs=[]
    p.on("console",lambda m: p._errs.append(m.text) if m.type=="error" and "api.github" not in m.text and "403" not in m.text else None)
    p.on("pageerror",lambda e: p._errs.append("PAGEERROR "+str(e)))
    p.on("request",lambda r: p._reqs.append(r.url))
    FIX=json.load(open(os.path.join(ROOT,'tests/fixtures/graphql-real-snapshot-2026-10-10.json')))['data']['user']['contributionsCollection']['contributionCalendar']
    LV={'NONE':0,'FIRST_QUARTILE':1,'SECOND_QUARTILE':2,'THIRD_QUARTILE':3,'FOURTH_QUARTILE':4}
    p.route("**/api/github-contributions",lambda r: r.fulfill(status=200,content_type="application/json",body=json.dumps({"username":"x","total":FIX['totalContributions'],"weeks":[[[d['date'],d['contributionCount'],LV[d['contributionLevel']]] for d in w['contributionDays']] for w in FIX['weeks']]})))
    p.route("https://api.github.com/**",lambda r: r.fulfill(status=200,content_type="application/json",body="[]" if "/repos" in r.request.url else "{}"))
    p.goto(URL,wait_until="load"); p.wait_for_timeout(500); return p
def go(p,sel):
    p.evaluate("(s)=>document.querySelector(s).scrollIntoView({block:'start',behavior:'instant'})",sel); p.wait_for_timeout(450)

with sync_playwright() as pw:
    b=pw.chromium.launch(**launch_kwargs())

    # ───────────── CERTIFICATES ─────────────
    p=page(b)
    check("games are NOT downloaded on first paint",not any('/games/' in u for u in p._reqs))
    n=p.locator(".cert-item").count()
    check("9 certificate cards rendered from data/certificates.json (count follows the data file)",n==9 and json.load(open(os.path.join(ROOT,'data/certificates.json')))['certificates'].__len__()==n)
    meta=p.evaluate("""()=>[...document.querySelectorAll('.cert-tile')].map(t=>({title:t.dataset.title,issuer:t.dataset.issuer,full:t.dataset.full,hasTitle:!!t.querySelector('.cert-title').textContent,hasView:/View certificate/.test(t.textContent)}))""")
    check("every card shows title, issuer and a View action",all(m['title'] and m['issuer'] and m['hasView'] for m in meta))
    check("every certificate file exists on disk",all(os.path.exists(os.path.join(ROOT,m['full'])) for m in meta))
    go(p,'#certificates'); p.wait_for_timeout(600)
    p.evaluate("document.querySelectorAll('.cert-thumb img').forEach(i=>i.scrollIntoView())"); p.wait_for_timeout(900)
    imgs=p.evaluate("[...document.querySelectorAll('.cert-thumb img')].map(i=>i.complete&&i.naturalWidth>0)")
    check("all 9 thumbnails load",all(imgs) and len(imgs)==9,str(imgs))
    p.screenshot(path=os.path.join(SHOTS,'certificates_gallery_1200.png'))
    for fid,exp in [('frontend',3),('data',4),('training',1),('other',1),('all',9)]:
        p.click(f'.cert-filter[data-filter="{fid}"]')
        vis=p.evaluate("[...document.querySelectorAll('.cert-item')].filter(e=>!e.hidden).length")
        pressed=p.get_attribute(f'.cert-filter[data-filter="{fid}"]','aria-pressed')
        check(f"filter '{fid}' shows {exp}, aria-pressed set, status announced",vis==exp and pressed=="true" and str(exp) in p.inner_text('#cert-status'),f"{vis} / {p.inner_text('#cert-status')}")
    # viewer
    tile=p.locator('.cert-tile').first; tile.focus(); tile.click(); p.wait_for_timeout(500)
    st=p.evaluate("""()=>({open:document.getElementById('cert-viewer').open,title:document.getElementById('cv-title').textContent,count:document.getElementById('cv-count').textContent,
        ready:document.getElementById('cv-img').classList.contains('is-ready'),nw:document.getElementById('cv-img').naturalWidth,alt:document.getElementById('cv-img').alt.length>20,
        inside:document.getElementById('cert-viewer').contains(document.activeElement),sub:document.getElementById('cv-sub').textContent})""")
    check("click opens viewer with title, counter, loaded image, descriptive alt, focus inside",st['open'] and st['title']=="React Frontend Web Developer" and st['count']=="1 / 9" and st['ready'] and st['nw']>0 and st['alt'] and st['inside'],str(st))
    p.screenshot(path=os.path.join(SHOTS,'certificates_viewer_1200.png'))
    p.click('#cv-next'); p.wait_for_timeout(300); c1=p.inner_text('#cv-count')
    p.keyboard.press('ArrowRight'); p.wait_for_timeout(300); c2=p.inner_text('#cv-count')
    p.keyboard.press('ArrowLeft'); p.wait_for_timeout(300); c3=p.inner_text('#cv-count')
    p.click('#cv-prev'); p.wait_for_timeout(300); c4=p.inner_text('#cv-count'); p.click('#cv-prev'); p.wait_for_timeout(300); c5=p.inner_text('#cv-count')
    check("Next/Prev buttons and ←/→ keys navigate; wraps around",(c1,c2,c3,c4,c5)==("2 / 9","3 / 9","2 / 9","1 / 9","9 / 9"),str((c1,c2,c3,c4,c5)))
    seen=set()
    for _ in range(14):
        p.keyboard.press('Tab'); seen.add(p.evaluate("document.getElementById('cert-viewer').contains(document.activeElement)"))
    check("focus is trapped inside the viewer while open (14 Tab presses)",seen=={True})
    p.keyboard.press('Escape'); p.wait_for_timeout(300)
    back=p.evaluate("({open:document.getElementById('cert-viewer').open,onTile:document.activeElement.classList.contains('cert-tile'),title:document.activeElement.dataset.title,lock:document.documentElement.classList.contains('cv-open')})")
    check("Escape closes and returns focus to the tile that opened it; scroll lock removed",not back['open'] and back['onTile'] and back['title']=="React Frontend Web Developer" and not back['lock'],str(back))
    p.locator('.cert-tile').nth(5).click(); p.wait_for_timeout(300); p.click('#cv-close'); p.wait_for_timeout(200)
    check("close button closes; focus restored to the 6th tile (Overview of AI)",p.evaluate("document.activeElement.dataset.title")=="Overview of AI")
    p.locator('.cert-tile').nth(2).click(); p.wait_for_timeout(300); p.mouse.click(5,5); p.wait_for_timeout(250)
    check("click outside (backdrop) closes the viewer",not p.evaluate("document.getElementById('cert-viewer').open"))
    p.click('.cert-filter[data-filter="data"]'); p.locator('.cert-tile:visible').first.click(); p.wait_for_timeout(300)
    seq=[]; 
    for _ in range(4): seq.append(p.inner_text('#cv-count')); p.keyboard.press('ArrowRight'); p.wait_for_timeout(250)
    check("navigation stays inside the active filter (Data & AI: 4 items)",seq==["1 / 4","2 / 4","3 / 4","4 / 4"],str(seq)); p.keyboard.press('Escape')
    # swipe
    p.click('.cert-filter[data-filter="all"]'); p.locator('.cert-tile').first.click(); p.wait_for_timeout(300)
    p.evaluate("""()=>{const s=document.getElementById('cv-stage');const f=(t,x)=>s.dispatchEvent(new PointerEvent(t,{pointerType:'touch',clientX:x,clientY:300,bubbles:true}));f('pointerdown',300);f('pointerup',120)}""")
    p.wait_for_timeout(300); check("swipe left goes to the next certificate",p.inner_text('#cv-count')=="2 / 9"); p.keyboard.press('Escape')
    check("no console errors on the certificate flow",not p._errs,str(p._errs[:2])); p.context.close()
    # image error state
    p=page(b); p.route("**/assets/certificates/itida-gigs-freelance-training.jpg",lambda r:r.fulfill(status=404,body=""))
    go(p,'#certificates'); p.locator('.cert-tile').nth(3).click(); p.wait_for_timeout(600)
    e=p.evaluate("({err:!document.getElementById('cv-error').hidden,state:document.getElementById('cv-state').hidden,href:document.getElementById('cv-open').getAttribute('href')})")
    check("missing image shows an error message with a direct link (loading state hidden)",e['err'] and e['state'] and e['href'].endswith('itida-gigs-freelance-training.jpg'),str(e)); p.context.close()
    # mobile viewer
    p=page(b,390,844,touch=True); go(p,'#certificates'); p.locator('.cert-tile').first.tap(); p.wait_for_timeout(600)
    m=p.evaluate("""()=>{const d=document.getElementById('cert-viewer').getBoundingClientRect();const i=document.getElementById('cv-img').getBoundingClientRect();return {w:d.width,h:d.height,iw:i.width,vw:innerWidth,vh:innerHeight,btn:[...document.querySelectorAll('.cv-btn')].every(b=>b.getBoundingClientRect().width>=44)}}""")
    check("mobile viewer fits the screen with 44px buttons",m['w']<=m['vw'] and m['h']<=m['vh'] and m['btn'],str(m))
    # regression: ITI is a portrait scan; tapping Next while it is shown resizes the dialog and used to close the viewer
    p.tap('#cv-next'); p.wait_for_timeout(500); p.tap('#cv-next'); p.wait_for_timeout(500); p.tap('#cv-next'); p.wait_for_timeout(500)
    r=p.evaluate("({open:document.getElementById('cert-viewer').open,count:document.getElementById('cv-count').textContent,title:document.getElementById('cv-title').textContent})")
    check("mobile: tapping Next through the portrait ITI scan keeps the viewer open (1→2→3→4)",r['open'] and r['count']=="4 / 9",str(r))
    p.screenshot(path=os.path.join(SHOTS,'certificates_viewer_390.png')); p.context.close()

    # ───────────── CERTIFICATE ORDER + NEW CERTIFICATES ─────────────
    p=page(b)
    order=p.evaluate("[...document.querySelectorAll('.cert-tile')].map(t=>t.dataset.title)")
    check("order: DEPI, then ITI, then NTI come first",order[:3]==["React Frontend Web Developer","Web Development using React","Web Designer — Summer Training"],str(order[:4]))
    meta=p.evaluate("""()=>Object.fromEntries([...document.querySelectorAll('.cert-item')].map(i=>[i.querySelector('.cert-title').textContent,{cat:i.dataset.category,text:i.textContent.replace(/\\s+/g,' ')}]))""")
    iti=meta.get("Web Development using React",{}); dc=meta.get("Introduction to SQL",{})
    check("ITI certificate: frontend category, issuer, dates and 144 hrs shown",iti.get('cat')=='frontend' and 'Information Technology Institute (ITI)' in iti.get('text','') and '12 Jul – 22 Aug 2026' in iti['text'] and '144 hrs' in iti['text'],str(iti))
    check("DataCamp certificate: data category, issuer, date and 2 hrs shown",dc.get('cat')=='data' and 'DataCamp' in dc.get('text','') and '30 Oct 2025' in dc['text'] and '2 hrs' in dc['text'],str(dc))
    cats=json.load(open(os.path.join(ROOT,'data/certificates.json')))['certificates']
    check("category set unchanged (frontend, data, training, other) and ids unique",{c['category'] for c in cats}=={'frontend','data','training','other'} and len({c['id'] for c in cats})==len(cats))
    p.context.close()

    # ───────────── PROJECTS: order, links, local screenshots ─────────────
    p=page(b); go(p,'#projects'); p.evaluate("document.querySelectorAll('#projects img').forEach(i=>i.scrollIntoView())"); p.wait_for_timeout(900)
    pr=p.evaluate("""()=>({names:[...document.querySelectorAll('#projects [data-project]')].map(e=>(e.querySelector('.feat-proj-name,.proj-name')||{}).textContent),
      hrefs:[...document.querySelectorAll('#projects a[href^=http]')].map(a=>a.href),
      imgs:[...document.querySelectorAll('#projects img')].map(i=>({src:i.getAttribute('src'),ok:i.complete&&i.naturalWidth>0,alt:i.alt.length>25,w:i.getAttribute('width'),h:i.getAttribute('height'),lazy:i.loading,nw:i.naturalWidth,nh:i.naturalHeight,rw:i.getBoundingClientRect().width,rh:i.getBoundingClientRect().height,fit:getComputedStyle(i).objectFit})),
      urlbar:document.querySelectorAll('.feat-proj-url')[1].textContent})""")
    check("project order: Furniture, Seif, Tawasol, then Power BI and Adidas last",[n.replace('&','&') for n in pr['names']]==["Furniture E-Commerce","Seif's Portfolio — Data Analyst","Tawasol","Power BI Sales Dashboard","Adidas Global Sales & Financial Performance Dashboard"],str(pr['names']))
    check("Seif uses the Vercel demo everywhere; old github.io URL is gone",pr['urlbar']=="seif-portfolio-nine.vercel.app" and sum(h=="https://seif-portfolio-nine.vercel.app/" for h in pr['hrefs'])==2 and not any('github.io' in h for h in pr['hrefs']) and "https://github.com/moustafax7-dotcom/seif-portfolio" in pr['hrefs'],str(pr['urlbar']))
    check("Power BI and Adidas link to their real repositories, no fake live demo",pr['hrefs'].count("https://github.com/moustafax7-dotcom/PowerBI-Sales-Data-Analysis")>=2 and pr['hrefs'].count("https://github.com/moustafax7-dotcom/Excel-adidas-Global-Sales-Analysis.")>=2 and not any('powerbi.com' in h or 'adidas' in h.split('github.com')[0] for h in pr['hrefs']))
    check("all project screenshots are local, loaded, have alt text and explicit width/height",all(i['src'].startswith('assets/projects/') and i['ok'] and i['alt'] and i['w'] and i['h'] for i in pr['imgs']) and len(pr['imgs'])==4,str(pr['imgs']))
    shot=[i for i in pr['imgs'] if 'sales-dashboard' in i['src']]
    check("analytics screenshots keep their full frame (<1% crop) and are lazy-loaded",len(shot)==2 and all(abs((i['rw']/i['rh'])/(i['nw']/i['nh'])-1)<0.01 and i['lazy']=='lazy' and i['fit']=='cover' for i in shot),str([(i['rw']/i['rh'],i['nw']/i['nh']) for i in shot]))
    for fn,(w,h) in {'powerbi-sales-dashboard.webp':(1138,740),'adidas-sales-dashboard.webp':(1086,679)}.items():
        from PIL import Image
        im=Image.open(os.path.join(ROOT,'assets/projects',fn)); check(f"{fn} is a real WebP at full resolution ({w}×{h})",im.format=='WEBP' and im.size==(w,h),str(im.size))
    check("no console errors in Projects",not p._errs,str(p._errs[:2]))
    p.screenshot(path=os.path.join(SHOTS,'projects_1200.png')); p.context.close()

    # ───────────── PLAYGROUND: Bug Hunter removed, Sushi Bounce is the only game ─────────────
    p=page(b)
    check("no game module is requested before the Playground is near the viewport",not any('/games/' in u for u in p._reqs))
    go(p,'#playground'); p.wait_for_selector('.sb canvas',timeout=5000)
    check("only sushi-bounce.js is loaded on demand; bug-hunter.js is never requested",any('sushi-bounce' in u for u in p._reqs) and not any('bug-hunter' in u for u in p._reqs))
    pg=p.evaluate("""()=>({tabs:document.querySelectorAll('.pg-tab,[role=tab],[role=tablist]').length,panels:document.querySelectorAll('.pg-panel').length,mounts:[...document.querySelectorAll('[data-mount]')].map(m=>m.dataset.mount),
      bh:document.querySelectorAll('.bh,[class*=bh-]').length,text:/bug hunter|bug-hunter|find the bug|buggy line/i.test(document.documentElement.innerHTML),
      visible:getComputedStyle(document.querySelector('#panel-sushi')).display!=='none',nav:[...document.querySelectorAll('a[href]')].some(a=>/bug/i.test(a.getAttribute('href')+a.textContent))})""")
    check("Playground has exactly one panel (Sushi Bounce), visible, no tabs, no Bug Hunter markup/text/links",pg['tabs']==0 and pg['panels']==1 and pg['mounts']==['sushi'] and pg['bh']==0 and not pg['text'] and pg['visible'] and not pg['nav'],str(pg))
    errs=list(p._errs)
    check("games/bug-hunter.js no longer exists on disk and the server answers 404",not os.path.exists(os.path.join(ROOT,'games','bug-hunter.js')) and p.evaluate("fetch('games/bug-hunter.js').then(r=>r.status)")==404)
    css=''.join(open(os.path.join(ROOT,f),encoding='utf-8').read() for f in ('style.css','assets/sections.css'))
    check("no leftover Bug Hunter CSS (.bh-*, .pg-tab*, syntax-token styles)",not re.search(r'\.bh[-\s{]|\.pg-tab|\.tk-[a-z]\b|@keyframes bh-',css))
    js=open(os.path.join(ROOT,'main.js'),encoding='utf-8').read()
    check("main.js has no Bug Hunter references",not re.search(r'bug',js,re.I))
    check("no console errors in the Playground",not errs,str(errs[:2])); p.context.close()

    # ───────────── SUSHI BOUNCE (mechanics verified against the reference source) ─────────────
    p=page(b); go(p,'#playground'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(300)
    st=lambda: p.evaluate("""()=>{const o=document.querySelector('.sb-overlay');return {overlayHidden:o.hidden,title:o.querySelector('h3')?.textContent,text:o.textContent,score:document.querySelector('[data-role=score]').textContent,lives:document.querySelector('[data-role=lives]').getAttribute('aria-label'),livesNum:document.querySelector('[data-role=lives] b').textContent,box:(r=>[Math.round(r.width),Math.round(r.height)])(document.querySelector('.sb-stage').getBoundingClientRect())}}""")
    s=st()
    check("Sushi loads on demand; start screen: title, 'Keep the sushi alive!', SCORE 0, LIVES 3",s['title']=="Sushi Bounce" and 'Keep the sushi alive!' in s['text'] and not s['overlayHidden'] and s['score']=="0" and s['livesNum']=="3" and s['lives']=="3 lives left",str(s))
    check("board size follows the reference: 700 × 430 px on desktop",s['box']==[700,430],str(s['box']))
    check("Sushi panel is a labelled region and is not hidden",p.get_attribute('#panel-sushi','role')=="region" and p.get_attribute('#panel-sushi','aria-label')=="Sushi Bounce game" and p.get_attribute('#panel-sushi','hidden') is None)
    p.screenshot(path=os.path.join(SHOTS,'sushi_start_1200.png'))
    p.evaluate("""async()=>{window.__m=await import('./games/sushi-bounce.js');const d=document.createElement('div');d.id='sandbox';d.style.cssText='position:fixed;left:0;top:0;width:700px;z-index:9;background:#000';document.body.append(d);window.__sb=window.__m.mount(d)}""")
    p.wait_for_timeout(300); g=lambda js: p.evaluate(js)
    s0=g("__sb.getState()"); check("initial: ready, no animation loop while idle, 3 lives, score 0",s0['mode']=="ready" and not s0['raf'] and s0['lives']==3 and s0['score']==0)
    p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()"); p.wait_for_timeout(60)
    s1=g("__sb.getState()")
    check("start: sushi 42px box centred at y=80, |vx|=|vy|=3 px/frame, paddle 110×15 centred, 22px above the bottom",
          s1['mode']=="playing" and s1['raf'] and abs(abs(s1['ball']['vx'])-3)<1e-9 and s1['ball']['vy']==3 and s1['paddle']=={'w':110,'h':15,'bottom':22} and abs(s1['paddleX']-(s1['board']['w']/2-55))<1e-6 and s1['board']['h']==430,str(s1))
    check("sushi spawns horizontally centred (x = width/2 − 21, y = 80)",abs(g("(__sb._setBall(__sb.getState().board.w/2-21,80,3,3),__sb.getState().ball.x)")-(g("__sb.getState().board.w")/2-21))<1e-6)
    # physics, one reference-frame per _step(): everything in a single JS task so the real loop cannot interfere
    r=g("""()=>{const a=__sb;a.start();a._forceMode('playing');const W=a.getState().board.w,H=a.getState().board.h;const o={};
      a._setBall(1,200,-3,3);a._step();o.left=a.getState().ball;
      a._setBall(W-42-1,200,3,3);a._step();o.right=a.getState().ball;o.W=W;
      a._setBall(100,1,3,-3);a._step();o.ceil=a.getState().ball;
      return o}""")
    check("walls: left edge clamps to 0 and flips vx; right edge clamps to width−42; ceiling clamps to 0 and flips vy",
          r['left']['x']==0 and r['left']['vx']==3 and r['right']['x']==r['W']-42 and r['right']['vx']==-3 and r['ceil']['y']==0 and r['ceil']['vy']==3,str(r))
    r=g("""()=>{const a=__sb;a.start();a._forceMode('playing');const top=430-22-15;a._setPaddle(300);const o={};
      a._setBall(300+55-21,top-42-1,3,3);a._step();o.hit=a.getState();
      a.start();a._forceMode('playing');a._setPaddle(300);a._setBall(300+55-21,top-42-1,-3,3);a._step();o.keep=a.getState().ball;
      return o}""")
    h=r['hit']
    check("paddle hit: score +1, sushi snapped on top of the paddle, bounces up, speed 3.08 on both axes (45° always)",h['score']==1 and h['ball']['y']==351 and abs(h['ball']['vy']+3.08)<1e-9 and abs(abs(h['ball']['vx'])-3.08)<1e-9,str(h['ball']))
    check("horizontal direction is kept on a hit (no angle control — as in the reference)",r['keep']['vx']<0 and abs(r['keep']['vx']+3.08)<1e-9)
    # centre-based collision window [paddleX, paddleX+110]
    r=g("""()=>{const a=__sb;const top=430-22-15;const out={};
      const t=(cx)=>{a.start();a._forceMode('playing');a._setPaddle(300);a._setBall(cx-21,top-42-1,3,3);a._step();return a.getState().score};
      /* the sushi moves 3 px (vx) before the check, so centre-after-move = cx+3 */ out.edgeL=t(297);out.beforeL=t(296);out.edgeR=t(407);out.afterR=t(408);
      a.start();a._forceMode('playing');a._setPaddle(300);a._setBall(335,top-42-1,3,-3);a._step();out.movingUp=a.getState().score;return out}""")
    check("collision uses the sushi's horizontal CENTRE: hit at centre = paddleX and paddleX+110, miss 1px outside; no hit while moving up",
          r=={'edgeL':1,'beforeL':0,'edgeR':1,'afterR':0,'movingUp':0},str(r))
    r=g("""()=>{const a=__sb;const top=430-22-15;const out=[];
      for(const s0 of [0,9,37,38,100]){a.start();a._forceMode('playing');a._setPaddle(300);a._setScore(s0);a._setBall(334,top-42-1,3,3);a._step();out.push([a.getState().score,+Math.abs(a.getState().ball.vx).toFixed(4)])}return out}""")
    check("difficulty: speed = 3 + min(score×0.08, 3) → 3.08 / 3.8 / 5.96 / 6 / 6 (capped at score 38)",r==[[1,3.08],[10,3.8],[38,6.0],[39,6.0],[101,6.0]] or r==[[1,3.08],[10,3.8],[38,6],[39,6],[101,6]],str(r))
    L=g("""()=>{const a=__sb;a.start();a._forceMode('playing');a._setScore(7);a._setPaddle(500);const out=[];
      for(let i=0;i<3;i++){if(a.getState().mode==='over')break;a._forceMode('playing');a._setBall(20,431,3,3);a._step();const s=a.getState();out.push([s.lives,s.mode,s.score,s.ball.y,Math.abs(s.ball.vx),s.ball.vy,s.paddleX])}return out}""")
    check("losing the sushi (top edge below the board): −1 life, respawn at y=80 with 3/3 px per frame, score and paddle unchanged; 3rd miss = game over",
          L[0][:3]==[2,'playing',7] and L[0][3]==80 and L[0][4]==3 and L[0][5]==3 and L[0][6]==500 and L[1][:2]==[1,'playing'] and L[2][:2]==[0,'over'],str(L))
    check("Game Over screen: 🍣, 'Oops!', 'Your sushi escaped.', final score, Play Again; loop stopped",
          p.inner_text('#sandbox .sb-overlay h3')=="Oops!" and 'Your sushi escaped.' in p.inner_text('#sandbox .sb-overlay') and 'Final score: 7' in p.inner_text('#sandbox .sb-overlay') and p.inner_text('#sandbox [data-role=primary]')=="Play Again" and '🍣' in p.inner_text('#sandbox .sb-overlay') and not g("__sb.getState().raf"))
    p.screenshot(path=os.path.join(SHOTS,'sushi_gameover_1200.png'))
    p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()"); p.wait_for_timeout(80)
    s3=g("__sb.getState()")
    check("Play Again resets score, lives, positions and velocities (HUD too)",s3['score']==0 and s3['lives']==3 and s3['mode']=="playing" and s3['ball']['y']>=80 and abs(s3['ball']['vy'])==3 and g("document.querySelector('#sandbox [data-role=score]').textContent")=="0" and g("document.querySelector('#sandbox [data-role=lives] b').textContent")=="3")
    # input: keyboard
    ok=g("""()=>{const a=__sb;a._forceMode('playing');a._setPaddle(300);return a.getState().paddleX}""")
    p.evaluate("document.querySelector('#sandbox .sb-stage').focus()"); sy0=g("scrollY")
    nud=g("""()=>{const a=__sb;a._setPaddle(300);const e=new KeyboardEvent('keydown',{key:'ArrowRight',cancelable:true,bubbles:true});window.dispatchEvent(e);const x=a.getState().paddleX;window.dispatchEvent(new KeyboardEvent('keyup',{key:'ArrowRight'}));return [x-300,e.defaultPrevented]}""")
    g("__sb._setPaddle(300)"); p.keyboard.down('ArrowRight'); p.wait_for_timeout(250); x2=g("__sb.getState().paddleX"); p.keyboard.up('ArrowRight'); x3=g("__sb.getState().paddleX"); p.wait_for_timeout(120); x4=g("__sb.getState().paddleX")
    check("keyboard: first → press nudges exactly 35 px (reference) and is cancelled so the page does not scroll; holding keeps moving; release stops",nud==[35,True] and x2>300+100 and x4==x3 and g("scrollY")==sy0,f"nudge={nud} held {x2-300:.0f}px, after release {x4-x3:.0f}")
    p.keyboard.down('a'); p.wait_for_timeout(200); xa=g("__sb.getState().paddleX"); p.keyboard.up('a'); check("A key moves the paddle left",xa<x4-60)
    pv=g("""()=>{let prevented=[];const f=e=>prevented.push(e.defaultPrevented);window.addEventListener('keydown',f);return prevented}""")
    d1=g("""()=>new Promise(r=>{const a=__sb;a.pause();const h=e=>{window.removeEventListener('keydown',h);setTimeout(()=>r(e.defaultPrevented),0)};window.addEventListener('keydown',h);document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',cancelable:true,bubbles:true}));window.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',cancelable:true,bubbles:true}))})""")
    check("arrow keys are NOT hijacked while the game is paused/not running (page can scroll)",d1 is False,str(d1))
    p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()"); p.wait_for_timeout(60)
    # pointer
    box=p.locator('#sandbox canvas').bounding_box(); p.mouse.move(box['x']+300,box['y']+200); p.wait_for_timeout(50)
    check("mouse movement centres the paddle on the pointer (no click needed)",abs(g("__sb.getState().paddleX")-(300-55))<2,str(g("__sb.getState().paddleX")))
    p.mouse.move(box['x']+1,box['y']+200); lft=g("__sb.getState().paddleX"); p.mouse.move(box['x']+box['width']-1,box['y']+200); rgt=g("__sb.getState().paddleX")
    check("paddle is clamped inside the board on both sides",lft==0 and abs(rgt-(g("__sb.getState().board.w")-110))<1e-6,f"{lft} {rgt}")
    # fixed timestep: same distance travelled at 60 Hz and 120 Hz (reference is frame-dependent)
    fr=p.evaluate("""async()=>{const out={};for(const [hz,frames] of [[60,60],[120,120],[144,144]]){let now=1000;const q=[];const rafO=window.requestAnimationFrame,cafO=window.cancelAnimationFrame,pnO=performance.now.bind(performance);
        window.requestAnimationFrame=cb=>(q.push(cb),q.length);window.cancelAnimationFrame=()=>{q.length=0};performance.now=()=>now;
        const d=document.createElement('div');document.body.append(d);const g=window.__m.mount(d);g.start();g._setBall(100,80,3,3);now+=0;
        for(let i=0;i<frames;i++){now+=1000/hz;const cb=q.shift();if(cb)cb(now)}
        const b=g.getState().ball;out[hz]=[Math.round(b.x),Math.round(b.y)];g.destroy();d.remove();window.requestAnimationFrame=rafO;window.cancelAnimationFrame=cafO;performance.now=pnO}return out}""")
    check("frame-rate independent: after 1 s the sushi is at the same place at 60, 120 and 144 Hz",fr['60']==fr['120']==fr['144'] or max(abs(fr['60'][0]-fr['120'][0]),abs(fr['60'][1]-fr['120'][1]),abs(fr['60'][0]-fr['144'][0]),abs(fr['60'][1]-fr['144'][1]))<=3,str(fr))
    # pause / resume
    p.evaluate("document.querySelector('#sandbox .sb-stage').focus()"); p.keyboard.press('p'); p.wait_for_timeout(100)
    sp=g("__sb.getState()"); check("P pauses: loop stops, Paused overlay shown",sp['mode']=="paused" and not sp['raf'] and p.inner_text('#sandbox .sb-overlay h3')=="Paused")
    before=g("__sb.getState().ball"); p.wait_for_timeout(300); after=g("__sb.getState().ball"); check("sushi does not move while paused",before==after)
    p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()"); p.wait_for_timeout(100)
    check("Resume continues the game",g("__sb.getState().mode")=="playing" and g("__sb.getState().raf"))
    p.keyboard.press('Escape'); p.wait_for_timeout(80); check("Esc also pauses",g("__sb.getState().mode")=="paused"); p.keyboard.press('p'); p.wait_for_timeout(80)
    p.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))"); p.wait_for_timeout(80)
    check("hidden browser tab auto-pauses the game",g("__sb.getState().mode")=="paused" and not g("__sb.getState().raf"))
    p.evaluate("delete document.hidden"); p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()")
    p.evaluate("document.getElementById('sandbox').style.top='-2000px'"); p.wait_for_timeout(300)
    check("scrolling the game off-screen auto-pauses it",g("__sb.getState().mode")=="paused"); p.evaluate("document.getElementById('sandbox').style.top='0'")
    # resize
    c0=g("__sb.getState().board"); p.evaluate("document.getElementById('sandbox').style.width='420px'"); p.wait_for_timeout(300); c1=g("__sb.getState().board"); cv=g("__sb.getState().canvas")
    check("board resizes with its container (canvas is DPR-aware); paddle and sushi stay inside",c1['w']<c0['w'] and c1['h']==430 and cv[0]>=c1['w'] and g("(()=>{const s=__sb.getState();return s.paddleX>=0&&s.paddleX<=s.board.w-110&&s.ball.x>=0&&s.ball.x<=s.board.w-42})()"),f"{c0}->{c1} canvas {cv}")
    leak=p.evaluate("""async()=>{const cnt={a:0,r:0};const wrap=(t)=>{const A=t.addEventListener,R=t.removeEventListener;t.addEventListener=function(...x){cnt.a++;return A.apply(this,x)};t.removeEventListener=function(...x){cnt.r++;return R.apply(this,x)}};
      wrap(window);wrap(document);const d=document.createElement('div');document.body.append(d);const g=window.__m.mount(d);g.start();await new Promise(r=>setTimeout(r,100));const s=g.getState();g.destroy();return {added:cnt.a,removed:cnt.r,raf:s.raf,after:d.childElementCount}}""")
    check("destroy() removes every window/document listener it added and empties the DOM",leak['removed']>=leak['added'] and leak['after']==0,str(leak))
    check("no console errors in Sushi Bounce",not p._errs,str(p._errs[:2])); p.context.close()

    # small screens: reference switches to a 380 px board and a 95×14 paddle at ≤700 px
    p=page(b,390,844,touch=True); go(p,'#playground'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(400)
    p.evaluate("""async()=>{const m=await import('./games/sushi-bounce.js');const d=document.createElement('div');d.id='sandbox';d.style.cssText='position:fixed;left:0;top:0;width:360px;z-index:9;background:#000';document.body.append(d);window.__sb=m.mount(d)}""")
    p.wait_for_timeout(300); p.evaluate("document.querySelector('#sandbox [data-role=primary]').click()"); p.wait_for_timeout(100)
    s=p.evaluate("__sb.getState()"); check("≤700 px viewport: board 380 px high, paddle 95×14, 20 px from the bottom (as in the reference CSS)",s['board']['h']==380 and s['paddle']=={'w':95,'h':14,'bottom':20},str(s['paddle'])+str(s['board']))
    cdp=p.context.new_cdp_session(p); box=p.locator('#sandbox canvas').bounding_box(); y=box['y']+box['height']*0.7
    cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[{"x":box['x']+box['width']*0.5,"y":y}]})
    for i in range(1,7): cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{"x":box['x']+box['width']*(0.5+0.07*i),"y":y}]})
    cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]}); p.wait_for_timeout(100)
    x1=p.evaluate("__sb.getState().paddleX"); target=box['width']*0.92-95/2
    check("touch drag moves the paddle, centred on the finger (CDP touch events)",abs(x1-target)<30,f"paddleX={x1:.0f} expected≈{target:.0f}")
    p.evaluate("__sb._forceMode('playing');__sb._setPaddle(60)")
    p.evaluate("document.querySelector('#sandbox .sb-pad button:last-child').dispatchEvent(new PointerEvent('pointerdown',{bubbles:true}))"); p.wait_for_timeout(250)
    x2=p.evaluate("__sb.getState().paddleX"); p.evaluate("document.querySelector('#sandbox .sb-pad button:last-child').dispatchEvent(new PointerEvent('pointerup',{bubbles:true}))")
    check("on-screen ◀ ▶ buttons are shown on touch devices and move the paddle",p.evaluate("getComputedStyle(document.querySelector('#sandbox .sb-pad')).display")=="flex" and x2>60+60,f"60->{x2:.0f}")
    p.evaluate("document.getElementById('sandbox').remove()"); go(p,'#panel-sushi'); p.screenshot(path=os.path.join(SHOTS,'sushi_mobile_390.png')); p.context.close()
    p=page(b,390,844,touch=True); go(p,'#playground'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(300)
    ta=p.evaluate("getComputedStyle(document.querySelector('.sb canvas')).touchAction")
    check("canvas declares touch-action: pan-y (vertical swipes keep scrolling the page; real-device swipe NOT automated — the reference blocks all touch scrolling over its board)",ta=="pan-y",ta); p.context.close()

    # ───────────── RESPONSIVE: every new section at 5 widths ─────────────
    for w,h in [(360,740),(390,844),(768,1024),(1200,800),(1440,900)]:
        p=page(b,w,h,touch=(w<700)); go(p,'#certificates'); p.evaluate("document.querySelectorAll('.cert-thumb img').forEach(i=>i.scrollIntoView())"); p.wait_for_timeout(500)
        go(p,'#playground'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(400)
        m=p.evaluate("""()=>{const de=document.documentElement;const bad=[];document.querySelectorAll('#certificates *, #playground *').forEach(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);if(r.width>0&&cs.position!=='fixed'&&cs.visibility!=='hidden'&&r.right>de.clientWidth+1)bad.push(e.className)});
          return {sw:de.scrollWidth,cw:de.clientWidth,bad:[...new Set(bad)].slice(0,4)}}""")
        check(f"certificates + playground: no overflow/clipping @{w}px",m['sw']<=m['cw'] and not m['bad'],str(m))
        if w in (390,1440): go(p,'#certificates'); p.screenshot(path=os.path.join(SHOTS,f'certificates_gallery_{w}.png')); go(p,'#skills'); p.screenshot(path=os.path.join(SHOTS,f'skills_{w}.png'))
        if w==1440: go(p,'#playground'); p.screenshot(path=os.path.join(SHOTS,'sushi_1440.png'))
        check(f"no console errors @{w}px",not p._errs,str(p._errs[:2])); p.context.close()

    # reduced motion + skills
    p=page(b,1200,800,reduced_motion="reduce"); go(p,'#playground'); p.wait_for_selector('.sb canvas')
    check("reduced motion: the game is idle until the player starts it (no auto-running loop)",p.evaluate("document.querySelector('.sb-overlay h3').textContent")=="Sushi Bounce"); 
    sk=p.evaluate("""()=>({groups:[...document.querySelectorAll('.sk-cat-title')].map(e=>e.textContent),cards:[...document.querySelectorAll('.sk-card span')].map(e=>e.textContent),rGlyph:getComputedStyle(document.querySelector('.devicon-r-plain'),'::before').content!=='none',font:document.fonts.check('16px devicon')})""")
    check("skills: 3 required groups, R + SQL + Power BI present, R icon from the local subset",sk['groups']==['Frontend Development','Data Analysis & Programming','Developer Tools'] and all(x in sk['cards'] for x in ['R','SQL','Power BI','Python','React']) and sk['rGlyph'],str(sk))
    check("no Pandas/NumPy/Matplotlib claimed (not confirmed)",not any(x in sk['cards'] for x in ['Pandas','NumPy','Matplotlib']))
    p.context.close(); b.close()

fails=[r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} checks passed"); sys.exit(1 if fails else 0)
