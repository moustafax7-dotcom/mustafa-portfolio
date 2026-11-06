"""GitHub section tests (REST + contribution calendar). Run: python3 tests/github.py [site_dir]
All network is mocked. Fixtures are REAL snapshots of the public GitHub pages taken on 2026-10-10:
  tests/fixtures/graphql-real-snapshot-2026-10-10.json  (371 days, 288 contributions)
  tests/fixtures/repos-real-snapshot-2026-10-10.json    (21 public repositories)
Follower/following numbers in the mocked user are synthetic test values."""
import sys, os, json, threading, http.server, socketserver
from playwright.sync_api import sync_playwright
from _launch import launch_kwargs
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

LV={'NONE':0,'FIRST_QUARTILE':1,'SECOND_QUARTILE':2,'THIRD_QUARTILE':3,'FOURTH_QUARTILE':4}
G=json.load(open(os.path.join(ROOT,'tests/fixtures/graphql-real-snapshot-2026-10-10.json')))['data']['user']['contributionsCollection']['contributionCalendar']
WEEKS=[[ [d['date'],d['contributionCount'],LV[d['contributionLevel']]] for d in w['contributionDays']] for w in G['weeks']]
PAYLOAD={"username":"moustafax7-dotcom","total":G['totalContributions'],"from":WEEKS[0][0][0],"to":WEEKS[-1][-1][0],"weeks":WEEKS,"generatedAt":"2026-10-10T08:00:00Z"}
REPOS=[{"name":r['name'],"description":r['description'],"language":r['language'],"stargazers_count":r['stars'],"pushed_at":r['pushed_at'],"updated_at":r['pushed_at'],"fork":r['fork'],"html_url":f"https://github.com/moustafax7-dotcom/{r['name']}"} for r in json.load(open(os.path.join(ROOT,'tests/fixtures/repos-real-snapshot-2026-10-10.json')))]
USER={"public_repos":len(REPOS),"followers":7,"following":9}
J=lambda body,status=200: dict(status=status,content_type="application/json",body=json.dumps(body))

def page(b,w=1200,h=800,rest="ok",contrib="ok",setup=None,**ctx):
    c=b.new_context(viewport={"width":w,"height":h},**ctx); p=c.new_page()
    p._errs=[]; p._calls={"gh":0,"fn":0}; p._contrib=contrib
    p.on("pageerror",lambda e: p._errs.append("PAGEERROR "+str(e)))
    def rest_route(r):
        p._calls["gh"]+=1
        if rest=="ok": r.fulfill(**J(REPOS if "/repos" in r.request.url else USER))
        elif rest=="403": r.fulfill(**J({"message":"API rate limit exceeded"},403))
        elif rest=="abort": r.abort()
        elif rest=="bad": r.fulfill(**J({"unexpected":True}))
        elif rest=="empty": r.fulfill(**J([] if "/repos" in r.request.url else USER))
    def fn_route(r):
        p._calls["fn"]+=1
        m={"ok":lambda:r.fulfill(**J(PAYLOAD)),
           "503":lambda:r.fulfill(**J({"error":"not_configured"},503)),"429":lambda:r.fulfill(**J({"error":"rate_limited"},429)),
           "auth":lambda:r.fulfill(**J({"error":"auth"},502)),"404html":lambda:r.fulfill(status=404,content_type="text/html",body="<h1>Not found</h1>"),
           "abort":lambda:r.abort(),"invalid":lambda:r.fulfill(**J({"total":5,"weeks":[["nope"]]})),
           "empty":lambda:r.fulfill(**J({**PAYLOAD,"total":0,"weeks":[[[d[0],0,0] for d in w] for w in WEEKS]})),
           "stale":lambda:r.fulfill(**J({**PAYLOAD,"stale":True}))}
        m[p._contrib]()
    p.route("https://api.github.com/**",rest_route); p.route("**/api/github-contributions",fn_route)
    if setup: setup(p)
    p.goto(URL,wait_until="load"); p.wait_for_timeout(400); return p
def to_github(p):
    p.evaluate("document.querySelector('#github').scrollIntoView({behavior:'instant'})"); p.wait_for_timeout(900)

with sync_playwright() as pw:
    b=pw.chromium.launch(**launch_kwargs())

    # lazy start
    p=page(b); check("no GitHub or /api request on first paint (section loads when near the viewport)",p._calls=={"gh":0,"fn":0},str(p._calls))
    to_github(p); p.wait_for_selector('.hm-cell[data-date]',timeout=5000)
    check("scrolling to the section triggers exactly 2 REST calls (user + repos) and 1 calendar call",p._calls=={"gh":2,"fn":1},str(p._calls))

    # calendar vs fixture
    cells=p.evaluate("[...document.querySelectorAll('.hm-cell[data-date]')].map(c=>[c.dataset.date,+c.dataset.count,+c.dataset.level])")
    exp=sorted([d for w in WEEKS for d in w]); got=sorted(cells)
    check("calendar renders all 371 real days with the exact counts and GitHub's own levels",got==exp and len(got)==371)
    check("genuine total shown in the title (288) and equals the sum of the daily counts",
          p.inner_text('#gh-graph-title').startswith('288 contributions in the last year') and sum(c[1] for c in cells)==288,p.inner_text('#gh-graph-title'))
    m=p.evaluate("""()=>({months:[...document.querySelectorAll('.hm-month')].map(e=>e.textContent).filter(Boolean),days:[...document.querySelectorAll('.hm-day')].map(e=>e.textContent),
        rows:document.querySelectorAll('.hm-table tbody tr').length,link:document.querySelector('.gh-graph-link').href,legend:document.querySelectorAll('.hm-legend .hm-cell').length,
        lbl:document.querySelector('.hm-cell[data-date="2026-10-03"]').getAttribute('aria-label'),zero:document.querySelector('.hm-cell[data-date="2025-10-05"]').getAttribute('aria-label')})""")
    check("month labels (Oct…Oct), Mon/Wed/Fri row labels, 7 rows, 5-step legend, link to the real profile",m['months'][0]=='Oct' and 'Jan' in m['months'] and len(m['months'])>=11 and m['days']==['','Mon','','Wed','','Fri',''] and m['rows']==7 and m['legend']==5 and m['link']=="https://github.com/moustafax7-dotcom","%s"%m['months'])
    check("accessible labels: dates and counts, singular/plural/none",m['lbl']=="1 contribution on Saturday, October 3, 2026" and m['zero']=="No contributions on Sunday, October 5, 2025",str((m['lbl'],m['zero'])))
    check("heatmap is a labelled grid in a keyboard-scrollable region",p.evaluate("document.querySelector('.hm-table').getAttribute('role')")=="grid" and p.evaluate("document.querySelector('.hm-scroll').tabIndex")==0)
    src=p.evaluate("renderContributionGraph.toString()+loadContributionGraph.toString()")
    check("no random/simulated data in the calendar code",'random' not in src.lower() and 'simulat' not in src.lower())
    # keyboard
    p.evaluate("document.querySelector('.hm-cell[tabindex=\"0\"]').focus()"); first=p.evaluate("document.activeElement.dataset.date")
    p.keyboard.press('ArrowLeft'); a=p.evaluate("document.activeElement.dataset.date"); p.keyboard.press('ArrowDown'); b2=p.evaluate("document.activeElement.dataset.row+'/'+document.activeElement.dataset.col")
    st=p.inner_text('.hm-status'); tabstops=p.evaluate("document.querySelectorAll('.hm-cell[tabindex=\"0\"]').length")
    check("grid keyboard: one tab stop, arrows move between days, status line announces the focused day",first=="2026-10-10" and a<first and tabstops==1 and 'contribution' in st.lower(),f"{first}->{a} {b2} | {st}")
    p.hover('.hm-cell[data-date="2026-03-02"]'); check("hover shows the day's text in the status line",'2026' in p.inner_text('.hm-status') and 'March 2, 2026' in p.inner_text('.hm-status'),p.inner_text('.hm-status'))
    p.evaluate("document.querySelector('#gh-graph').scrollIntoView({block:'center'})"); p.wait_for_timeout(300); p.screenshot(path=os.path.join(SHOTS,'github_calendar_1200.png'))

    # repositories
    r=p.evaluate("""()=>({names:[...document.querySelectorAll('#repos-live .repo-name')].map(e=>e.textContent),hidden:document.getElementById('repos-live').hidden,fbHidden:document.getElementById('repos-list').hidden,
        badge:document.getElementById('repos-badge')?.textContent||document.querySelector('#repos-lbl .gh-badge').textContent,lbl:document.getElementById('repos-lbl').textContent,
        descs:[...document.querySelectorAll('#repos-live .repo-desc')].map(e=>[e.textContent,e.classList.contains('is-empty')]),
        stats:[document.getElementById('gh-repos').textContent,document.getElementById('gh-follow').textContent,document.getElementById('gh-fing').textContent],
        langHidden:document.getElementById('langs-box').hidden,langs:[...document.querySelectorAll('.lang-name')].map(e=>e.textContent),note:document.querySelector('.gh-lang-note').textContent,
        links:[...document.querySelectorAll('#repos-live a')].every(a=>a.href.startsWith('https://github.com/moustafax7-dotcom/')&&a.rel.includes('noopener')),
        meta:[...document.querySelectorAll('#repos-live .repo-card')].map(c=>[!!c.querySelector('.repo-lang'),/^Updated /.test(c.querySelector('.repo-upd')?.textContent||''),c.querySelector('.repo-stars')?.textContent])})""")
    check("latest 6 repositories sorted by pushed_at (forks & profile repos excluded)",r['names']==['-React-Summer-Training---ITI','fasfoor-project','github-practice','mustafa-portfolio','BT','Abdulrahman-Abdulrazek-portfolio'],str(r['names']))
    check("live list replaces the static snapshot and is labelled 'live from GitHub'",not r['hidden'] and r['fbHidden'] and 'live from GitHub' in r['lbl'] and 'Latest updated' in r['lbl'])
    check("descriptions are GitHub's own; missing ones say 'No description provided' (nothing invented)",r['descs'][2]==['A repository for practicing GitHub workflows and collaboration',False] and r['descs'][0]==['No description provided',True] and sum(1 for d in r['descs'] if d[1])==5,str(r['descs']))
    check("each card has language (or 'No language detected'), stars, 'Updated …' and a direct repo link",all(m[0] and m[1] and m[2] for m in r['meta']) and r['links'],str(r['meta'][:2]))
    check("profile stats come from the API response (repos/followers/following)",r['stats']==[str(len(REPOS)),'7','9'],str(r['stats']))
    check("language share is computed from repositories, worded as repository contents (not proficiency)",not r['langHidden'] and 'HTML' in r['langs'] and 'not coding proficiency' in r['note'],str(r['langs']))
    p.screenshot(path=os.path.join(SHOTS,'github_dashboard_1200.png')); p.evaluate("document.querySelector('#repos-lbl').scrollIntoView({block:'start'})"); p.wait_for_timeout(200); p.screenshot(path=os.path.join(SHOTS,'github_repos_1200.png'))
    check("no console errors on the success path",not p._errs,str(p._errs)); p.context.close()

    # selectLatestRepos unit checks
    p=page(b)
    u=p.evaluate("""()=>{const R=(n,t,f)=>({name:n,pushed_at:t,fork:!!f});const L=[R('old','2025-01-01T00:00:00Z'),R('new','2026-10-01T00:00:00Z'),R('fork','2026-10-09T00:00:00Z',true),R('moustafax7-dotcom','2026-10-10T00:00:00Z'),R('moustafax7-dotcom.github.io','2026-10-10T00:00:00Z'),R('bad-date','nope'),R('Mid','2026-05-01T00:00:00Z')];
      return {a:selectLatestRepos(L).map(r=>r.name),b:selectLatestRepos(L,{limit:2}).map(r=>r.name),c:selectLatestRepos(L,{hidden:['NEW']}).map(r=>r.name),d:selectLatestRepos(null),e:selectLatestRepos([])}}""")
    check("selectLatestRepos: newest push first, forks/profile repos skipped, invalid dates last, limit + hidden list respected, safe on bad input",
          u['a']==['new','Mid','old','bad-date'] and u['b']==['new','Mid'] and u['c']==['Mid','old','bad-date'] and u['d']==[] and u['e']==[],str(u)); p.context.close()

    # REST failures
    for label,mode in [("rate limit (403)","403"),("network failure","abort"),("unexpected response shape","bad")]:
        p=page(b,rest=mode); to_github(p); p.wait_for_timeout(300)
        r=p.evaluate("""()=>({fb:!document.getElementById('repos-list').hidden,live:document.getElementById('repos-live').hidden,cards:document.querySelectorAll('#repos-list .repo-card').length,
            note:document.getElementById('gh-note').hidden?'':document.getElementById('gh-note').textContent,stats:document.getElementById('gh-repos').textContent,badge:document.getElementById('repos-badge').textContent,
            stars:document.querySelectorAll('.repo-stars').length,langs:document.getElementById('langs-box').hidden})""")
        check(f"REST {label}: static snapshot stays, labelled 'not live', honest note, no invented stats",r['fb'] and r['live'] and r['cards']==4 and 'unavailable' in r['note'] and r['stats']=="—" and 'not live' in r['badge'] and r['stars']==0 and r['langs'],str(r))
        p.context.close()
    p=page(b,rest="empty"); to_github(p)
    check("REST empty repository list: snapshot kept, stats still real (no crash)",not p.evaluate("document.getElementById('repos-list').hidden") and p._errs==[] ); p.context.close()
    p=page(b,rest="403"); to_github(p)
    snap=p.evaluate("""()=>[...document.querySelectorAll('#repos-list .repo-card')].map(c=>[c.querySelector('.repo-name').textContent,c.querySelector('.repo-desc').textContent,c.querySelector('.repo-desc').classList.contains('is-empty')])""")
    check("static snapshot uses real descriptions (Tawasol's own text) and honest 'No description provided' for the rest",snap[0][1]=="Tawasol Platform — DEPI 2025 — React.js" and all(s[2] for s in snap[1:]),str(snap)); p.context.close()

    # caching
    p=page(b); to_github(p); p.wait_for_timeout(300); n1=p._calls['gh']; p.reload(wait_until="load"); p.wait_for_timeout(300); to_github(p); p.wait_for_timeout(500)
    cached=p.evaluate("!!JSON.parse(localStorage.getItem('portfolio:github:v2')).repos.length")
    check("cache: second visit within 30 min makes no GitHub REST request and renders from the saved copy",cached and p._calls['gh']==n1 and p.locator('#repos-live .repo-card').count()==6,f"{n1}->{p._calls['gh']}"); 
    p.evaluate("""()=>{const c=JSON.parse(localStorage.getItem('portfolio:github:v2'));c.savedAt=Date.now()-3*3600*1000;localStorage.setItem('portfolio:github:v2',JSON.stringify(c))}"""); p.context.close()
    def stale_setup(p):
        p.add_init_script("""localStorage.setItem('portfolio:github:v2',JSON.stringify({savedAt:Date.now()-3*3600*1000,user:{public_repos:3,followers:1,following:2},repos:[{name:'cached-repo',description:null,language:'CSS',stargazers_count:0,pushed_at:'2026-09-01T00:00:00Z',fork:false,html_url:'https://github.com/moustafax7-dotcom/cached-repo'}]}))""")
    p=page(b,rest="403",setup=stale_setup); to_github(p); p.wait_for_timeout(300)
    check("expired cache + GitHub unreachable: stale data shown with an explicit 'Live update failed… saved 3 hr ago' note",p.locator('#repos-live .repo-name').first.inner_text()=="cached-repo" and 'Live update failed' in p.inner_text('#gh-note') and '3 hr ago' in p.inner_text('#gh-note'),p.inner_text('#gh-note')); p.context.close()

    # calendar failure states
    for label,mode,needle,retry in [("not configured (503)","503","not enabled",False),("rate limited (429)","429","request limit",True),("auth error","auth","temporarily unavailable",True),
                                    ("function missing (HTML 404)","404html","not enabled",False),("network failure","abort","could not be reached",True),("invalid payload","invalid","temporarily unavailable",True)]:
        p=page(b,contrib=mode); to_github(p); p.wait_for_timeout(400)
        msg=p.inner_text('#gh-graph-body'); cells=p.locator('.hm-cell[data-date]').count(); lnk=p.get_attribute('#gh-graph-body a','href')
        check(f"calendar {label}: honest message, link to real profile, {'retry button' if retry else 'no retry'}, zero fake cells",needle in msg and cells==0 and lnk=="https://github.com/moustafax7-dotcom" and (p.locator('#gh-graph-body .pg-btn').count()==1)==retry and 'auth' not in msg.lower().replace('author',''),msg.replace('\n',' ')[:110])
        p.context.close()
    p=page(b,contrib="empty"); to_github(p); p.wait_for_selector('.hm-cell[data-date]')
    check("empty calendar (0 contributions): renders genuine zeros, title says 0",p.inner_text('#gh-graph-title').startswith('0 contributions') and p.evaluate("[...document.querySelectorAll('.hm-cell[data-date]')].every(c=>c.dataset.level==='0')")); p.context.close()
    p=page(b,contrib="stale"); to_github(p); p.wait_for_selector('.hm-cell[data-date]')
    check("stale server copy is labelled as such",'last saved copy' in p.inner_text('#gh-graph-body')); p.context.close()
    # offline
    p=page(b); p._contrib="abort"; p.context.set_offline(True); to_github(p); p.wait_for_timeout(1200)
    check("offline: calendar says you appear to be offline (retry offered), no crash",'offline' in p.inner_text('#gh-graph-body') and p.locator('#gh-graph-body .pg-btn').count()==1 and not p._errs,p.inner_text('#gh-graph-body')[:80])
    p._contrib="ok"; p.context.set_offline(False); p.wait_for_selector('.hm-cell[data-date]',timeout=5000)
    check("coming back online reloads the calendar automatically",p.locator('.hm-cell[data-date]').count()==371); p.context.close()
    p=page(b,contrib="429"); to_github(p); p.wait_for_timeout(400); p._contrib="ok"; p.click('#gh-graph-body .pg-btn'); p.wait_for_selector('.hm-cell[data-date]',timeout=5000)
    check("'Try again' button reloads the calendar after a rate-limit error",p.locator('.hm-cell[data-date]').count()==371 and p.locator('#gh-graph-body .pg-btn').count()==0); p.context.close()
    # skeleton while loading (slow function)
    def slow(p): p.add_init_script("const f=window.fetch;window.fetch=(u,...a)=>String(u).includes('github-contributions')?new Promise(r=>setTimeout(()=>r(f(u,...a)),1500)):f(u,...a)")
    p=page(b,setup=slow); p.evaluate("document.querySelector('#github').scrollIntoView({behavior:'instant'})"); p.wait_for_timeout(500)
    check("loading state: skeleton with aria-busy and a status message, then the calendar",p.locator('.hm-skeleton').count()==1 and p.get_attribute('#gh-graph-body','aria-busy')=="true"); p.wait_for_selector('.hm-cell[data-date]',timeout=6000); p.context.close()

    # active nav link works for sections taller than the viewport (the GitHub section is tall)
    p=page(b,1440,900); res={}
    for sid in ['about','skills','projects','github','experience','certificates','contact']:
        p.evaluate("(s)=>{const e=document.getElementById(s);window.scrollTo({top:scrollY+e.getBoundingClientRect().top-60,behavior:'instant'})}",sid); p.wait_for_timeout(450)
        res[sid]=p.evaluate("[...document.querySelectorAll('.n-links a.active')].map(a=>a.getAttribute('href'))")
    check("nav highlights the section being read, including the tall GitHub section",all(v==['#'+k] for k,v in res.items()),str(res)); p.context.close()

    # responsive: no overflow, calendar scrolls inside its own region
    for w,h in [(360,740),(390,844),(768,1024),(1200,800),(1440,900)]:
        p=page(b,w,h,touch=w<700) if False else page(b,w,h); to_github(p); p.wait_for_selector('.hm-cell[data-date]'); p.wait_for_timeout(300)
        m=p.evaluate("""()=>{const de=document.documentElement;const s=document.querySelector('.hm-scroll');const bad=[];document.querySelectorAll('#github *').forEach(e=>{const r=e.getBoundingClientRect();if(r.width>0&&r.right>de.clientWidth+1&&!e.closest('.hm-scroll'))bad.push(e.className)});
          return {sw:de.scrollWidth,cw:de.clientWidth,scrolls:s.scrollWidth>s.clientWidth,atEnd:Math.abs(s.scrollLeft+s.clientWidth-s.scrollWidth)<2,bad:[...new Set(bad)].slice(0,3)}}""")
        check(f"GitHub section @{w}px: no page overflow; calendar scrolls inside its own region{' and opens on the latest weeks' if w<800 else ''}",m['sw']<=m['cw'] and not m['bad'] and (m['scrolls'] and m['atEnd'] if w<800 else True),str(m))
        if w in (390,1440): p.evaluate("document.querySelector('#github').scrollIntoView()"); p.wait_for_timeout(200); p.screenshot(path=os.path.join(SHOTS,f'github_section_{w}.png'))
        p.context.close()
    b.close()
fails=[r for r in results if not r[1]]
print(f"\n{len(results)-len(fails)}/{len(results)} checks passed"); sys.exit(1 if fails else 0)
