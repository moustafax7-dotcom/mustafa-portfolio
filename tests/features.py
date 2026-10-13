"""Feature tests: certificates gallery + viewer, Bug Hunter, Sushi Bounce, responsive, cleanup.
Run: python3 tests/features.py [site_dir]   (nothing real is sent; GitHub/Formspree are mocked)"""
import sys, os, threading, http.server, socketserver, json
from playwright.sync_api import sync_playwright
ROOT=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),'..'))
SHOTS=os.path.join(ROOT,'docs','screenshots'); os.makedirs(SHOTS,exist_ok=True)
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
    b=pw.chromium.launch()

    # ───────────── CERTIFICATES ─────────────
    p=page(b)
    check("games are NOT downloaded on first paint",not any('/games/' in u for u in p._reqs))
    n=p.locator(".cert-item").count()
    check("7 certificate cards rendered from data/certificates.json",n==7 and json.load(open(os.path.join(ROOT,'data/certificates.json')))['certificates'].__len__()==7)
    meta=p.evaluate("""()=>[...document.querySelectorAll('.cert-tile')].map(t=>({title:t.dataset.title,issuer:t.dataset.issuer,full:t.dataset.full,hasTitle:!!t.querySelector('.cert-title').textContent,hasView:/View certificate/.test(t.textContent)}))""")
    check("every card shows title, issuer and a View action",all(m['title'] and m['issuer'] and m['hasView'] for m in meta))
    check("every certificate file exists on disk",all(os.path.exists(os.path.join(ROOT,m['full'])) for m in meta))
    go(p,'#certificates'); p.wait_for_timeout(600)
    p.evaluate("document.querySelectorAll('.cert-thumb img').forEach(i=>i.scrollIntoView())"); p.wait_for_timeout(900)
    imgs=p.evaluate("[...document.querySelectorAll('.cert-thumb img')].map(i=>i.complete&&i.naturalWidth>0)")
    check("all 7 thumbnails load",all(imgs) and len(imgs)==7,str(imgs))
    p.screenshot(path=os.path.join(SHOTS,'certificates_gallery_1200.png'))
    for fid,exp in [('frontend',2),('data',3),('training',1),('other',1),('all',7)]:
        p.click(f'.cert-filter[data-filter="{fid}"]')
        vis=p.evaluate("[...document.querySelectorAll('.cert-item')].filter(e=>!e.hidden).length")
        pressed=p.get_attribute(f'.cert-filter[data-filter="{fid}"]','aria-pressed')
        check(f"filter '{fid}' shows {exp}, aria-pressed set, status announced",vis==exp and pressed=="true" and str(exp) in p.inner_text('#cert-status'),f"{vis} / {p.inner_text('#cert-status')}")
    # viewer
    tile=p.locator('.cert-tile').first; tile.focus(); tile.click(); p.wait_for_timeout(500)
    st=p.evaluate("""()=>({open:document.getElementById('cert-viewer').open,title:document.getElementById('cv-title').textContent,count:document.getElementById('cv-count').textContent,
        ready:document.getElementById('cv-img').classList.contains('is-ready'),nw:document.getElementById('cv-img').naturalWidth,alt:document.getElementById('cv-img').alt.length>20,
        inside:document.getElementById('cert-viewer').contains(document.activeElement),sub:document.getElementById('cv-sub').textContent})""")
    check("click opens viewer with title, counter, loaded image, descriptive alt, focus inside",st['open'] and st['title']=="React Frontend Web Developer" and st['count']=="1 / 7" and st['ready'] and st['nw']>0 and st['alt'] and st['inside'],str(st))
    p.screenshot(path=os.path.join(SHOTS,'certificates_viewer_1200.png'))
    p.click('#cv-next'); p.wait_for_timeout(300); c1=p.inner_text('#cv-count')
    p.keyboard.press('ArrowRight'); p.wait_for_timeout(300); c2=p.inner_text('#cv-count')
    p.keyboard.press('ArrowLeft'); p.wait_for_timeout(300); c3=p.inner_text('#cv-count')
    p.click('#cv-prev'); p.wait_for_timeout(300); c4=p.inner_text('#cv-count'); p.click('#cv-prev'); p.wait_for_timeout(300); c5=p.inner_text('#cv-count')
    check("Next/Prev buttons and ←/→ keys navigate; wraps around",(c1,c2,c3,c4,c5)==("2 / 7","3 / 7","2 / 7","1 / 7","7 / 7"),str((c1,c2,c3,c4,c5)))
    seen=set()
    for _ in range(14):
        p.keyboard.press('Tab'); seen.add(p.evaluate("document.getElementById('cert-viewer').contains(document.activeElement)"))
    check("focus is trapped inside the viewer while open (14 Tab presses)",seen=={True})
    p.keyboard.press('Escape'); p.wait_for_timeout(300)
    back=p.evaluate("({open:document.getElementById('cert-viewer').open,onTile:document.activeElement.classList.contains('cert-tile'),title:document.activeElement.dataset.title,lock:document.documentElement.classList.contains('cv-open')})")
    check("Escape closes and returns focus to the tile that opened it; scroll lock removed",not back['open'] and back['onTile'] and back['title']=="React Frontend Web Developer" and not back['lock'],str(back))
    p.locator('.cert-tile').nth(3).click(); p.wait_for_timeout(300); p.click('#cv-close'); p.wait_for_timeout(200)
    check("close button closes; focus restored to 4th tile",p.evaluate("document.activeElement.dataset.title")=="Overview of AI")
    p.locator('.cert-tile').nth(2).click(); p.wait_for_timeout(300); p.mouse.click(5,5); p.wait_for_timeout(250)
    check("click outside (backdrop) closes the viewer",not p.evaluate("document.getElementById('cert-viewer').open"))
    p.click('.cert-filter[data-filter="data"]'); p.locator('.cert-tile:visible').first.click(); p.wait_for_timeout(300)
    seq=[]; 
    for _ in range(3): seq.append(p.inner_text('#cv-count')); p.keyboard.press('ArrowRight'); p.wait_for_timeout(250)
    check("navigation stays inside the active filter (Data & AI: 3 items)",seq==["1 / 3","2 / 3","3 / 3"],str(seq)); p.keyboard.press('Escape')
    # swipe
    p.click('.cert-filter[data-filter="all"]'); p.locator('.cert-tile').first.click(); p.wait_for_timeout(300)
    p.evaluate("""()=>{const s=document.getElementById('cv-stage');const f=(t,x)=>s.dispatchEvent(new PointerEvent(t,{pointerType:'touch',clientX:x,clientY:300,bubbles:true}));f('pointerdown',300);f('pointerup',120)}""")
    p.wait_for_timeout(300); check("swipe left goes to the next certificate",p.inner_text('#cv-count')=="2 / 7"); p.keyboard.press('Escape')
    check("no console errors on the certificate flow",not p._errs,str(p._errs[:2])); p.context.close()
    # image error state
    p=page(b); p.route("**/assets/certificates/itida-gigs-freelance-training.jpg",lambda r:r.fulfill(status=404,body=""))
    go(p,'#certificates'); p.locator('.cert-tile').nth(2).click(); p.wait_for_timeout(600)
    e=p.evaluate("({err:!document.getElementById('cv-error').hidden,state:document.getElementById('cv-state').hidden,href:document.getElementById('cv-open').getAttribute('href')})")
    check("missing image shows an error message with a direct link (loading state hidden)",e['err'] and e['state'] and e['href'].endswith('itida-gigs-freelance-training.jpg'),str(e)); p.context.close()
    # mobile viewer
    p=page(b,390,844,touch=True); go(p,'#certificates'); p.locator('.cert-tile').first.tap(); p.wait_for_timeout(600)
    m=p.evaluate("""()=>{const d=document.getElementById('cert-viewer').getBoundingClientRect();const i=document.getElementById('cv-img').getBoundingClientRect();return {w:d.width,h:d.height,iw:i.width,vw:innerWidth,vh:innerHeight,btn:[...document.querySelectorAll('.cv-btn')].every(b=>b.getBoundingClientRect().width>=44)}}""")
    check("mobile viewer fits the screen with 44px buttons",m['w']<=m['vw'] and m['h']<=m['vh'] and m['btn'],str(m))
    p.screenshot(path=os.path.join(SHOTS,'certificates_viewer_390.png')); p.context.close()

    # ───────────── BUG HUNTER ─────────────
    p=page(b)
    check("Bug Hunter module not requested before the section is near",not any('bug-hunter' in u for u in p._reqs))
    go(p,'#playground'); p.wait_for_selector('.bh .bh-line',timeout=5000)
    check("Bug Hunter loads on demand; Sushi module still not requested",any('bug-hunter' in u for u in p._reqs) and not any('sushi-bounce' in u for u in p._reqs))
    def line(n): return p.locator(f'.bh-line[data-line="{n}"]')
    q1=p.inner_text('.bh-q'); line(3).click()
    s1=p.evaluate("({ok:document.querySelector('.bh-line.is-correct')?.dataset.line,fb:document.querySelector('.bh-feedback').className,score:document.querySelector('[data-role=score]').textContent,dis:[...document.querySelectorAll('.bh-line')].every(l=>l.getAttribute('aria-disabled')==='true')})")
    check("correct answer: line highlighted, ✓ feedback with explanation, score 1, lines locked",s1['ok']=="3" and 'ok' in s1['fb'] and s1['score']=="1" and s1['dis'] and 'NaN' in p.inner_text('.bh-feedback'),str(s1))
    line(1).click(force=True); check("answering twice is ignored",p.inner_text('[data-role=score]')=="1" and p.locator('.bh-line.is-wrong').count()==0)
    p.screenshot(path=os.path.join(SHOTS,'bug_hunter_answered_1200.png'))
    p.click('[data-role=next]'); p.wait_for_timeout(200)
    check("Next moves to question 2, progress bar advances, focus lands in the code",'Question 2 of 7' in p.inner_text('.bh-q') and p.get_attribute('.bh-bar','aria-valuenow')=="1" and p.evaluate("document.activeElement.classList.contains('bh-line')"))
    line(1).click()   # wrong (bug is line 2)
    w=p.evaluate("({wrong:document.querySelector('.bh-line.is-wrong')?.dataset.line,right:document.querySelector('.bh-line.is-correct')?.dataset.line,fb:document.querySelector('.bh-feedback').className})")
    check("wrong answer: chosen line red, real bug line green, ✗ feedback, score unchanged",w=={'wrong':'1','right':'2','fb':'bh-feedback no'} and p.inner_text('[data-role=score]')=="1",str(w))
    p.click('[data-role=next]')
    # keyboard-only Q3: focus code, ArrowDown, press 3
    p.evaluate("document.querySelector('.bh-line').focus()"); p.keyboard.press('ArrowDown')
    check("ArrowDown moves focus between lines",p.evaluate("document.activeElement.dataset.line")=="2")
    p.keyboard.press('3'); check("pressing '3' answers with line 3 (keyboard only), score 2",p.inner_text('[data-role=score]')=="2" and p.locator('.bh-line.is-correct[data-line="3"]').count()==1)
    p.keyboard.press('Enter'); p.wait_for_timeout(150)
    check("Enter on the focused Next button advances (Q4)",'Question 4 of 7' in p.inner_text('.bh-q'))
    # finish: Q4 correct(2), Q5 wrong, Q6 correct(2), Q7 wrong
    for ans in [2,1,2,1]:
        line(ans).click(); p.click('[data-role=next]'); p.wait_for_timeout(120)
    end=p.inner_text('.bh-end h3')
    check("score calculation: 4 correct of 7 → 'You found 4 of 7 bugs'",end=="You found 4 of 7 bugs" and p.get_attribute('.bh-bar','aria-valuenow')=="7",end)
    p.screenshot(path=os.path.join(SHOTS,'bug_hunter_results_1200.png'))
    p.click('[data-role=again]'); p.wait_for_timeout(150)
    check("restart resets score, progress and question",p.inner_text('[data-role=score]')=="0" and 'Question 1 of 7' in p.inner_text('.bh-q') and p.get_attribute('.bh-bar','aria-valuenow')=="0")
    p.click('.bh-level[data-level=medium]'); p.wait_for_timeout(100)
    check("Medium level: 4 questions, pressed state updates",'of 4' in p.inner_text('.bh-q') and p.get_attribute('.bh-level[data-level=medium]','aria-pressed')=="true")
    # every shipped question has exactly one valid answer within its snippet
    ok=p.evaluate("""async()=>{const src=await (await fetch('games/bug-hunter.js')).text();const m=src.match(/const QUESTIONS = (\\[[\\s\\S]*?\\n\\]);/);const Q=(0,eval)(m[1]);return Q.every(q=>q.bug>=1&&q.bug<=q.code.length&&q.explain.length>40)&&Q.length===11}""")
    check("question bank sane: 11 questions, bug line inside each snippet, explanations present",ok)
    check("no console errors in Bug Hunter",not p._errs,str(p._errs[:2])); p.context.close()

    # ───────────── SUSHI BOUNCE (mechanics verified against the reference source) ─────────────
    p=page(b); go(p,'#playground'); p.wait_for_selector('.bh-line'); p.click('#tab-sushi'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(300)
    st=lambda: p.evaluate("""()=>{const o=document.querySelector('.sb-overlay');return {overlayHidden:o.hidden,title:o.querySelector('h3')?.textContent,text:o.textContent,score:document.querySelector('[data-role=score]').textContent,lives:document.querySelector('[data-role=lives]').getAttribute('aria-label'),livesNum:document.querySelector('[data-role=lives] b').textContent,box:(r=>[Math.round(r.width),Math.round(r.height)])(document.querySelector('.sb-stage').getBoundingClientRect())}}""")
    s=st()
    check("Sushi loads on tab selection; start screen: title, 'Keep the sushi alive!', SCORE 0, LIVES 3",s['title']=="Sushi Bounce" and 'Keep the sushi alive!' in s['text'] and not s['overlayHidden'] and s['score']=="0" and s['livesNum']=="3" and s['lives']=="3 lives left",str(s))
    check("board size follows the reference: 700 × 430 px on desktop",s['box']==[700,430],str(s['box']))
    check("Bug Hunter panel hidden, tab roles/aria-selected correct",p.get_attribute('#panel-bug','hidden') is not None and p.get_attribute('#tab-sushi','aria-selected')=="true" and p.get_attribute('#tab-bug','aria-selected')=="false")
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
    p=page(b,390,844,touch=True); go(p,'#playground'); p.wait_for_selector('.bh-line'); p.tap('#tab-sushi'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(400)
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
    p=page(b,390,844,touch=True); go(p,'#playground'); p.wait_for_selector('.bh-line'); p.tap('#tab-sushi'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(300)
    ta=p.evaluate("getComputedStyle(document.querySelector('.sb canvas')).touchAction")
    check("canvas declares touch-action: pan-y (vertical swipes keep scrolling the page; real-device swipe NOT automated — the reference blocks all touch scrolling over its board)",ta=="pan-y",ta); p.context.close()

    # ───────────── RESPONSIVE: every new section at 5 widths ─────────────
    for w,h in [(360,740),(390,844),(768,1024),(1200,800),(1440,900)]:
        p=page(b,w,h,touch=(w<700)); go(p,'#certificates'); p.evaluate("document.querySelectorAll('.cert-thumb img').forEach(i=>i.scrollIntoView())"); p.wait_for_timeout(500)
        go(p,'#playground'); p.wait_for_selector('.bh-line'); p.click('#tab-sushi'); p.wait_for_selector('.sb canvas'); p.wait_for_timeout(400)
        m=p.evaluate("""()=>{const de=document.documentElement;const bad=[];document.querySelectorAll('#certificates *, #playground *').forEach(e=>{const r=e.getBoundingClientRect();const cs=getComputedStyle(e);if(r.width>0&&cs.position!=='fixed'&&cs.visibility!=='hidden'&&r.right>de.clientWidth+1&&!e.closest('.bh-code'))bad.push(e.className)});
          return {sw:de.scrollWidth,cw:de.clientWidth,bad:[...new Set(bad)].slice(0,4),tabs:[...document.querySelectorAll('.pg-tab')].map(t=>t.getBoundingClientRect().height>=44)}}""")
        check(f"certificates + playground: no overflow/clipping @{w}px",m['sw']<=m['cw'] and not m['bad'] and all(m['tabs']),str(m))
        if w in (390,1440): go(p,'#certificates'); p.screenshot(path=os.path.join(SHOTS,f'certificates_gallery_{w}.png')); go(p,'#skills'); p.screenshot(path=os.path.join(SHOTS,f'skills_{w}.png'))
        if w==1440: go(p,'#playground'); p.screenshot(path=os.path.join(SHOTS,'sushi_1440.png')); p.click('#tab-bug'); p.wait_for_timeout(200); p.screenshot(path=os.path.join(SHOTS,'bug_hunter_1440.png'))
        check(f"no console errors @{w}px",not p._errs,str(p._errs[:2])); p.context.close()

    # reduced motion + skills
    p=page(b,1200,800,reduced_motion="reduce"); go(p,'#playground'); p.wait_for_selector('.bh-line'); p.click('#tab-sushi'); p.wait_for_selector('.sb canvas')
    check("reduced motion: the game is idle until the player starts it (no auto-running loop)",p.evaluate("document.querySelector('.sb-overlay h3').textContent")=="Sushi Bounce"); 
    sk=p.evaluate("""()=>({groups:[...document.querySelectorAll('.sk-cat-title')].map(e=>e.textContent),cards:[...document.querySelectorAll('.sk-card span')].map(e=>e.textContent),rGlyph:getComputedStyle(document.querySelector('.devicon-r-plain'),'::before').content!=='none',font:document.fonts.check('16px devicon')})""")
    check("skills: 3 required groups, R + SQL + Power BI present, R icon from the local subset",sk['groups']==['Frontend Development','Data Analysis & Programming','Developer Tools'] and all(x in sk['cards'] for x in ['R','SQL','Power BI','Python','React']) and sk['rGlyph'],str(sk))
    check("no Pandas/NumPy/Matplotlib claimed (not confirmed)",not any(x in sk['cards'] for x in ['Pandas','NumPy','Matplotlib']))
    p.context.close(); b.close()

fails=[r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} checks passed"); sys.exit(1 if fails else 0)
