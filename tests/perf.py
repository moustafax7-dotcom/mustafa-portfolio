"""Performance guards + interaction timing (lab, Chromium, 4x CPU throttle, mobile emulation).
Run: python3 tests/perf.py [site_dir]   — writes docs/perf-results.json with the measured numbers.
These are regression guards for the main-thread problems found in the v2 audit (docs/REPORT.md)."""
import sys, os, re, json, threading, http.server, socketserver, statistics as st
from playwright.sync_api import sync_playwright
ROOT=os.path.abspath(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(__file__),'..'))
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s,*a,**k): super().__init__(*a,directory=ROOT,**k)
    def log_message(s,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(("127.0.0.1",0),Q); PORT=srv.server_address[1]
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL=f"http://127.0.0.1:{PORT}/index.html"
results=[]; numbers={}
def check(name,ok,detail=""):
    results.append((name,bool(ok),detail)); print(("PASS " if ok else "FAIL ")+name+(f"  [{detail}]" if detail else ""))

# ── static: nothing that loops forever may animate layout- or paint-heavy properties ──
css=open(os.path.join(ROOT,'style.css'),encoding='utf-8').read()+open(os.path.join(ROOT,'assets/sections.css'),encoding='utf-8').read()
infinite=set(re.findall(r'animation:[^;{}]*?\b([a-zA-Z][\w-]*)\b[^;{}]*?infinite',css))
infinite|=set(re.findall(r'animation-name:\s*([\w-]+)[^}]*?animation-iteration-count:\s*infinite',css))
bad={}
for name in infinite:
    m=re.search(r'@keyframes\s+'+re.escape(name)+r'\s*\{(.*?)\n\}',css,re.S)
    if not m: continue
    props=set(re.findall(r'([a-z-]+)\s*:',m.group(1)))
    heavy=props-{'transform','opacity','background-position'}
    if heavy: bad[name]=sorted(heavy)
check("every looping CSS animation only animates transform/opacity (or the loading-skeleton background-position)",not bad and len(infinite)>=5,f"infinite={sorted(infinite)} offenders={bad}")

with sync_playwright() as pw:
    b=pw.chromium.launch()
    def mobile(throttle=4):
        c=b.new_context(viewport={"width":412,"height":823},device_scale_factor=1.75,is_mobile=True,has_touch=True); p=c.new_page()
        p._reqs=[]; p.on("request",lambda r:p._reqs.append(r.url))
        p.route("https://**",lambda r:r.abort()); p.route("**/api/github-contributions",lambda r:r.fulfill(status=503,content_type="application/json",body='{"error":"not_configured"}'))
        cdp=c.new_cdp_session(p); cdp.send("Performance.enable"); cdp.send("Emulation.setCPUThrottlingRate",{"rate":throttle})
        p.add_init_script("""window.__lt=[];new PerformanceObserver(l=>{for(const e of l.getEntries())window.__lt.push([e.startTime,e.duration])}).observe({type:'longtask',buffered:true});
          window.__fcp=0;new PerformanceObserver(l=>{for(const e of l.getEntries())if(e.name==='first-contentful-paint')window.__fcp=e.startTime}).observe({type:'paint',buffered:true});
          window.__ev=[];new PerformanceObserver(l=>{for(const e of l.getEntries())window.__ev.push([e.name,Math.round(e.duration),Math.round(e.processingEnd-e.processingStart)])}).observe({type:'event',durationThreshold:16,buffered:true});""")
        p._cdp=cdp; return p
    def metrics(p): return {x['name']:x['value'] for x in p._cdp.send("Performance.getMetrics")['metrics']}

    # ── initial load on a throttled phone ──
    runs=[]
    for _ in range(3):
        p=mobile(); p.goto(URL,wait_until="load"); p.wait_for_timeout(3500); m=metrics(p)
        info=p.evaluate("""()=>({lt:window.__lt,fcp:window.__fcp,dot:document.getElementById('hcanvas').width,gameCanvas:document.querySelectorAll('.sb-canvas').length,nodes:document.querySelectorAll('*').length,
          running:document.getAnimations().filter(a=>a.playState==='running'&&a.effect.getTiming().iterations===Infinity).map(a=>[a.animationName||a.transitionProperty||'?',Object.keys(a.effect.getKeyframes()[0]).filter(k=>!['offset','computedOffset','easing','composite'].includes(k)).join('+')])})""")
        tbt=sum(max(0,d-50) for t,d in info['lt'] if t>=info['fcp'])
        runs.append(dict(layouts=m['LayoutCount'],recalcs=m['RecalcStyleCount'],task=m['TaskDuration']*1000,tbt=tbt,reqs=list(p._reqs),info=info)); p.context.close()
    med=lambda k: round(st.median(r[k] for r in runs),1)
    numbers['load_4x_cpu']={k:med(k) for k in ['layouts','recalcs','task','tbt']}; numbers['dom_nodes']=runs[0]['info']['nodes']
    check("load @4x CPU, phone: ≤ 100 layouts and ≤ 160 style recalcs in 3.5 s (v2 had ~180 / ~240)",med('layouts')<=100 and med('recalcs')<=160,str(numbers['load_4x_cpu']))
    check("load @4x CPU, phone: total main-thread task time ≤ 2100 ms (v2: ~2800)",med('task')<=2100)
    check("load @4x CPU, phone: blocking time after FCP ≤ 150 ms",med('tbt')<=150)
    r0=runs[0]
    check("lazy: no GitHub / /api / games / certificate-full-size requests during the initial load",not any(('api.github' in u or '/api/' in u or '/games/' in u or re.search(r'assets/certificates/[^/]+(?<!-thumb)\\.jpg',u)) for u in r0['reqs']),str([u for u in r0['reqs'] if 'games' in u or 'certificates' in u][:3]))
    check("lazy: no game canvas exists until a game is opened; hero dot canvas is NOT built on phones (static CSS pattern instead)",r0['info']['gameCanvas']==0 and r0['info']['dot']==300)
    run=r0['info']['running']; heavy=[x for x in run if set(x[1].split('+'))-{'transform','opacity'}]
    check("phone: every looping animation that is running only animates transform/opacity",not heavy,str(run))
    numbers['phone_running_infinite_animations']=run

    # ── hero animation pauses when scrolled away ──
    p=mobile(1); p.goto(URL,wait_until="load"); p.wait_for_timeout(600)
    p.evaluate("window.scrollTo({top:2500,behavior:'instant'})"); p.wait_for_timeout(500)
    off=p.evaluate("({cls:document.documentElement.classList.contains('hero-off'),state:getComputedStyle(document.querySelector('.cv-shine')).animationPlayState})")
    check("hero animations pause (html.hero-off) when the hero is off-screen",off['cls'] and off['state']=='paused',str(off)); p.context.close()

    # ── desktop: dot canvas only for a fine pointer; cursor not set up until a mouse moves ──
    c=b.new_context(viewport={"width":1440,"height":900}); p=c.new_page(); p.route("https://**",lambda r:r.abort()); p.goto(URL,wait_until="load"); p.wait_for_timeout(800)
    d=p.evaluate("({canvas:document.getElementById('hcanvas').width>300,cursor:document.documentElement.classList.contains('has-cursor')})")
    check("desktop: animated dot canvas is built; custom cursor still dormant until the first mouse move",d['canvas'] and not d['cursor'],str(d)); c.close()

    # ── interaction timing (Event Timing + wall clock), 4x CPU ──
    p=mobile(); p.goto(URL,wait_until="load"); p.wait_for_timeout(1500)
    def tap_time(sel,wait=250,scroll=True):
        if scroll: p.evaluate("(s)=>document.querySelector(s).scrollIntoView({block:'center',behavior:'instant'})",sel); p.wait_for_timeout(300)
        p.evaluate("window.__ev.length=0"); p.tap(sel); p.wait_for_timeout(wait)
        ev=p.evaluate("window.__ev"); return max([e[1] for e in ev] or [0])
    inter={}
    p.evaluate("document.querySelector('#certificates').scrollIntoView({behavior:'instant'})"); p.wait_for_timeout(2500)  # let the lazy GitHub work finish: we measure the interaction, not background work
    def med3(fn): vals=[fn() for _ in range(3)]; return round(st.median(vals))
    def toggle_filter():
        v=tap_time('.cert-filter[data-filter="frontend"]',wait=500,scroll=False); tap_time('.cert-filter[data-filter="all"]',wait=500,scroll=False); return v
    inter['certificate filter']=med3(toggle_filter)
    def open_close():
        v=tap_time('.cert-item:not([hidden]) .cert-tile',wait=900,scroll=False); p.keyboard.press('Escape'); p.wait_for_timeout(500); return v
    inter['open certificate viewer']=med3(open_close)
    tap_time('.cert-item:not([hidden]) .cert-tile',wait=900,scroll=False)
    inter['next certificate']=med3(lambda: tap_time('#cv-next',wait=700,scroll=False))
    p.keyboard.press('Escape'); p.wait_for_timeout(300)
    t0=p.evaluate("""()=>new Promise(res=>{const t=performance.now();document.querySelector('#playground').scrollIntoView({behavior:'instant'});const iv=setInterval(()=>{if(document.querySelector('.bh-line')){clearInterval(iv);res(performance.now()-t)}},16)})""")
    numbers['bug_hunter_ready_ms']=round(t0)
    def bh_answer():
        p.evaluate("document.querySelector('.bh-level[data-level=easy]').click()"); p.wait_for_timeout(600)
        return tap_time('.bh-line[data-line="3"]',wait=500,scroll=False)
    inter['Bug Hunter: answer a line']=med3(bh_answer)
    p.evaluate("document.querySelector('#tab-sushi').scrollIntoView({block:'center',behavior:'instant'})"); p.wait_for_timeout(200)
    t1=p.evaluate("""()=>new Promise(res=>{const t=performance.now();document.querySelector('#tab-sushi').click();const iv=setInterval(()=>{if(document.querySelector('.sb-canvas')){clearInterval(iv);res(performance.now()-t)}},16)})""")
    numbers['sushi_module_load_and_mount_ms']=round(t1)
    p.wait_for_timeout(400); inter['Sushi Bounce: Start Game']=tap_time('.sb-overlay [data-role=primary]',wait=400)
    numbers['interaction_ms_at_4x_cpu']=inter
    check("interactions @4x CPU: filter, next, Bug Hunter answer and Sushi Start each respond in < 200 ms (INP 'good' budget)",all(v<200 for k,v in inter.items() if k!='open certificate viewer'),str(inter))
    check("opening the certificate viewer (native modal <dialog>, whole page becomes inert) < 260 ms @4x CPU — borderline vs the 200 ms INP budget on a 4x-throttled phone",inter['open certificate viewer']<260,str(inter['open certificate viewer']))
    check("opening a game for the first time (import + mount) takes < 600 ms @4x CPU",t0<600 and t1<600,f"bug={round(t0)}ms sushi={round(t1)}ms")

    # ── gameplay frame cost @4x CPU: 4 s of play ──
    fr=p.evaluate("""async()=>{const times=[];let last=performance.now();const lt=[];new PerformanceObserver(l=>{for(const e of l.getEntries())lt.push(e.duration)}).observe({type:'longtask'});
      await new Promise(res=>{const loop=t=>{times.push(t-last);last=t;times.length<240?requestAnimationFrame(loop):res()};requestAnimationFrame(loop)});
      times.shift();times.sort((a,b)=>a-b);return {median:times[times.length>>1],p95:times[Math.floor(times.length*0.95)],max:times[times.length-1],longtasks:lt.length}}""")
    numbers['gameplay_frames_4x_cpu']={k:round(v,1) for k,v in fr.items()}
    gs=p.evaluate("""()=>{const o=document.querySelector('.sb-overlay');return {playing:o.hidden}}""")
    check("sushi is actually playing during the frame measurement",gs['playing'])
    check("gameplay @4x CPU: median frame ≤ 20 ms, p95 ≤ 40 ms, no long tasks (60 fps held even on a throttled phone)",fr['median']<=20 and fr['p95']<=40 and fr['longtasks']==0,str(numbers['gameplay_frames_4x_cpu']))
    p.context.close(); b.close()

json.dump(numbers,open(os.path.join(ROOT,'docs','perf-results.json'),'w'),indent=1)
fails=[r for r in results if not r[1]]
print("\nmeasured:",json.dumps(numbers)[:900])
print(f"\n{len(results)-len(fails)}/{len(results)} checks passed"); sys.exit(1 if fails else 0)
