from __future__ import annotations
import os, json, sqlite3, hashlib, re, asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
UPLOADS = DATA / 'uploads'
DB = DATA / 'careeros.db'
UPLOADS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='CareerOS', version='0.1.0', description='Local-first personal career operating system')
app.mount('/static', StaticFiles(directory=ROOT / 'frontend'), name='static')

DEFAULT_PROFILE = {
  'name': 'Aditi Jain', 'salary_min_lpa': 15, 'salary_max_lpa': 18,
  'locations': ['Remote','Bengaluru','Gurgaon / Delhi NCR','Hyderabad','Pune','Mumbai','Noida','International remote'],
  'employment_types': ['Full-time'], 'briefing_time': '09:00', 'timezone': 'Asia/Kolkata',
  'application_policy': 'Prepare everything and ask before every submission',
  'role_families': ['AI Engineer','Agentic AI Engineer','LLM Engineer','Applied AI Engineer','AI Automation Engineer','Generative AI Engineer','AI Product Engineer','Backend Engineer','AI Solutions Engineer','Founders Office - Technology'],
  'summary': 'AI product and engineering professional with experience building LLM-powered document workflows, automation systems and full-stack applications.'
}
SEED_PROJECTS = [
 {'name':'Fee-Schedule Automation Platform','category':'Professional experience','organization':'Moody’s Ratings','description':'End-to-end platform for annual pricing updates: bulk PDF ingestion, multimodal LLM extraction, structured review/editing, L1/L2 approvals and publishing to downstream billing systems. Built with Java, Spring Boot, Spring WebFlux, Spring AI, Kafka and Angular. Business-rule validation and targeted LLM repair support human-reviewed extraction. Reported turnaround reduction of approximately 75%.','skills':['Java','Spring Boot','Spring WebFlux','Spring AI','Kafka','Angular','Multimodal LLMs','Human-in-the-loop','Document AI'],'status':'experience'},
 {'name':'PIVerse / Process Intelligence & AI Transformation Platform','category':'Independent project','description':'Platform concept for reconstructing hierarchical business workflows, identifying bottlenecks and evaluating where AI interventions are suitable. Includes agent-assisted what-if simulation comparing human-led, automated and agent-augmented workflows on performance, cost and risk.','skills':['AI agents','Process intelligence','Workflow analysis','Simulation'],'status':'in_progress'},
 {'name':'EmoQuest','category':'Project','description':'AI-assisted affective behaviour tracking system with four game environments capturing avoidance, reaction latency, expressive positivity and voice interactions.','skills':['AI','Behaviour tracking','Voice interaction'],'status':'project'},
 {'name':'EduSight','category':'Project','description':'Academic monitoring and anomaly detection system for attendance, grades and assignments, generating individualized academic insights.','skills':['Python','Analytics','Anomaly detection'],'status':'project'},
 {'name':'EEDO','category':'Venture','description':'E-waste initiative connecting e-waste generators with authorized recyclers. Associated with the Technovation Global Winner recognition. Add evidence and personal contribution details in Project Studio.','skills':['Social impact','Product development'],'status':'venture'},
 {'name':'QEasy','category':'Venture','description':'Virtual queue management concept using tokens and time slots to reduce physical waiting during COVID-era operations. Historical project notes mention pilot/testing with shopkeepers and consumers; verify metrics and personal contribution before using externally.','skills':['Product strategy','Customer discovery'],'status':'venture'},
 {'name':'i-Code / ORO','category':'Initiative','description':'Cyber-safety education and awareness initiatives covering phishing, fake news, cyberbullying, scams and online safety. Historical profile notes mention workshops and an ORO cyber-safety app; verify reach and individual contribution before publishing.','skills':['Cybersecurity awareness','Community building'],'status':'initiative'},
 {'name':'Girls in Technology','category':'Leadership initiative','description':'Mentoring and outreach supporting girls in app development and computational thinking. Historical profile notes mention 1,000+ girls reached and multiple ambassador years; attach supporting evidence before external use.','skills':['Mentoring','Leadership','Community building'],'status':'initiative'}
]

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init_db():
    with connect() as c:
      c.executescript('''
      CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT DEFAULT 'Project', organization TEXT DEFAULT '', description TEXT DEFAULT '', skills TEXT DEFAULT '[]', status TEXT DEFAULT 'project', created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS assets (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER, filename TEXT NOT NULL, stored_path TEXT NOT NULL, content_type TEXT, extracted_text TEXT DEFAULT '', uploaded_at TEXT NOT NULL, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE SET NULL);
      CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, external_id TEXT, title TEXT NOT NULL, company TEXT NOT NULL, location TEXT DEFAULT '', url TEXT NOT NULL, description TEXT DEFAULT '', posted_at TEXT, salary TEXT DEFAULT '', employment_type TEXT DEFAULT 'Full-time', score INTEGER DEFAULT 0, score_reasons TEXT DEFAULT '[]', status TEXT DEFAULT 'discovered', first_seen TEXT NOT NULL, UNIQUE(source, external_id));
      CREATE TABLE IF NOT EXISTS applications (id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, resume_version TEXT DEFAULT '', answers TEXT DEFAULT '{}', notes TEXT DEFAULT '', status TEXT DEFAULT 'prepared', approved_at TEXT, submitted_at TEXT, created_at TEXT NOT NULL, FOREIGN KEY(job_id) REFERENCES jobs(id));
      CREATE TABLE IF NOT EXISTS outreach (id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, person TEXT DEFAULT '', role TEXT DEFAULT '', email TEXT DEFAULT '', source_url TEXT DEFAULT '', reason TEXT DEFAULT '', subject TEXT DEFAULT '', body TEXT DEFAULT '', status TEXT DEFAULT 'draft', created_at TEXT NOT NULL, approved_at TEXT, sent_at TEXT);
      CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL, board_token TEXT NOT NULL, active INTEGER DEFAULT 1, UNIQUE(kind, board_token));
      CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);
      ''')
      row=c.execute('SELECT id FROM profile WHERE id=1').fetchone()
      if not row: c.execute('INSERT INTO profile(id,data,updated_at) VALUES(1,?,?)',(json.dumps(DEFAULT_PROFILE),now()))
      if c.execute('SELECT COUNT(*) n FROM projects').fetchone()['n']==0:
        for p in SEED_PROJECTS: c.execute('INSERT INTO projects(name,category,organization,description,skills,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(p['name'],p.get('category','Project'),p.get('organization',''),p['description'],json.dumps(p['skills']),p['status'],now(),now()))
      if c.execute('SELECT COUNT(*) n FROM sources').fetchone()['n']==0:
        c.execute("INSERT INTO sources(kind,name,board_token) VALUES('greenhouse','Example Greenhouse board','example')")
        c.execute("INSERT INTO sources(kind,name,board_token) VALUES('lever','Example Lever board','example')")
      c.commit()

def now(): return datetime.now(timezone.utc).isoformat()
def rowdict(r): return dict(r) if r else None
def event(kind,msg):
    with connect() as c: c.execute('INSERT INTO events(kind,message,created_at) VALUES(?,?,?)',(kind,msg,now()))
def parse_job_date(v):
    if not v: return None
    try:
      if isinstance(v,(int,float)): return datetime.fromtimestamp(v/1000 if v>10**11 else v,timezone.utc).isoformat()
      return str(v)
    except: return None

class ProjectIn(BaseModel):
    name:str; category:str='Project'; organization:str=''; description:str=''; skills:list[str]=[]; status:str='project'
class ProfileIn(BaseModel): data:dict
class SourceIn(BaseModel): kind:str; name:str; board_token:str
class ApplicationIn(BaseModel): job_id:int; resume_version:str=''; answers:dict={}; notes:str=''
class OutreachIn(BaseModel): company:str; person:str=''; role:str=''; email:str=''; source_url:str=''; reason:str=''; subject:str=''; body:str=''

@app.on_event('startup')
def startup(): init_db()

@app.get('/',response_class=HTMLResponse)
def home(): return FileResponse(ROOT/'frontend'/'index.html')
@app.get('/api/health')
def health(): return {'status':'ok','version':'0.1.0','database':str(DB),'time':now()}
@app.get('/api/profile')
def get_profile():
    with connect() as c: return json.loads(c.execute('SELECT data FROM profile WHERE id=1').fetchone()['data'])
@app.put('/api/profile')
def put_profile(payload:ProfileIn):
    with connect() as c: c.execute('UPDATE profile SET data=?,updated_at=? WHERE id=1',(json.dumps(payload.data),now()))
    event('profile','Career profile updated'); return {'ok':True}
@app.get('/api/projects')
def projects():
    with connect() as c: rows=c.execute('SELECT * FROM projects ORDER BY updated_at DESC').fetchall()
    out=[]
    for r in rows:
      d=rowdict(r); d['skills']=json.loads(d['skills']); out.append(d)
    return out
@app.post('/api/projects')
def add_project(p:ProjectIn):
    with connect() as c:
      cur=c.execute('INSERT INTO projects(name,category,organization,description,skills,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(p.name,p.category,p.organization,p.description,json.dumps(p.skills),p.status,now(),now()))
      pid=cur.lastrowid
    event('project',f'Project created: {p.name}'); return {'id':pid,'ok':True}
@app.put('/api/projects/{pid}')
def update_project(pid:int,p:ProjectIn):
    with connect() as c:
      cur=c.execute('UPDATE projects SET name=?,category=?,organization=?,description=?,skills=?,status=?,updated_at=? WHERE id=?',(p.name,p.category,p.organization,p.description,json.dumps(p.skills),p.status,now(),pid))
      if cur.rowcount==0: raise HTTPException(404,'Project not found')
    return {'ok':True}
@app.delete('/api/projects/{pid}')
def delete_project(pid:int):
    with connect() as c: c.execute('DELETE FROM projects WHERE id=?',(pid,))
    return {'ok':True}

@app.post('/api/projects/{pid}/upload')
async def upload_asset(pid:int,file:UploadFile=File(...)):
    with connect() as c:
      if not c.execute('SELECT id FROM projects WHERE id=?',(pid,)).fetchone(): raise HTTPException(404,'Project not found')
    safe=re.sub(r'[^A-Za-z0-9._-]','_',file.filename or 'upload')
    raw=await file.read(); digest=hashlib.sha256(raw).hexdigest()[:12]
    path=UPLOADS/f'{digest}_{safe}'; path.write_bytes(raw)
    extracted=''
    try:
      suffix=path.suffix.lower()
      if suffix=='.pdf':
        import fitz
        doc=fitz.open(path); extracted='\n'.join(page.get_text() for page in doc)[:100000]
      elif suffix=='.docx':
        from docx import Document
        extracted='\n'.join(p.text for p in Document(path).paragraphs)[:100000]
      elif suffix=='.pptx':
        from pptx import Presentation
        prs=Presentation(path); extracted='\n'.join(sh.text for sl in prs.slides for sh in sl.shapes if hasattr(sh,'text'))[:100000]
      elif suffix in ['.txt','.md','.json','.py','.java','.js','.ts','.tsx','.html','.css']:
        extracted=raw.decode('utf-8',errors='ignore')[:100000]
    except Exception as e: extracted=f'[Text extraction unavailable: {e}]'
    with connect() as c:
      cur=c.execute('INSERT INTO assets(project_id,filename,stored_path,content_type,extracted_text,uploaded_at) VALUES(?,?,?,?,?,?)',(pid,file.filename,str(path),file.content_type,extracted,now()))
    event('asset',f'Uploaded {file.filename} to project {pid}')
    return {'id':cur.lastrowid,'filename':file.filename,'extracted_characters':len(extracted),'extracted_text_preview':extracted[:1500]}
@app.get('/api/projects/{pid}/assets')
def assets(pid:int):
    with connect() as c: rows=c.execute('SELECT id,filename,content_type,extracted_text,uploaded_at FROM assets WHERE project_id=? ORDER BY uploaded_at DESC',(pid,)).fetchall()
    return [dict(r)|{'extracted_text_preview':r['extracted_text'][:500]} for r in rows]

@app.get('/api/sources')
def get_sources():
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM sources ORDER BY id').fetchall()]
@app.post('/api/sources')
def add_source(s:SourceIn):
    if s.kind not in ('greenhouse','lever'): raise HTTPException(400,'Supported source types: greenhouse, lever')
    with connect() as c:
      try: cur=c.execute('INSERT INTO sources(kind,name,board_token) VALUES(?,?,?)',(s.kind,s.name,s.board_token.strip()))
      except sqlite3.IntegrityError: raise HTTPException(409,'This board is already configured')
    return {'id':cur.lastrowid,'ok':True}
@app.delete('/api/sources/{sid}')
def delete_source(sid:int):
    with connect() as c: c.execute('DELETE FROM sources WHERE id=?',(sid,))
    return {'ok':True}

async def fetch_greenhouse(client, token):
    url=f'https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true'
    r=await client.get(url,timeout=25); r.raise_for_status()
    for j in r.json().get('jobs',[]):
      yield {'source':'greenhouse','external_id':str(j.get('id')),'title':j.get('title','Untitled'),'company':token,'location':(j.get('location') or {}).get('name',''),'url':j.get('absolute_url',''),'description':re.sub('<[^>]+>',' ',j.get('content','')),'posted_at':parse_job_date(j.get('updated_at'))}
async def fetch_lever(client, token):
    url=f'https://api.lever.co/v0/postings/{token}?mode=json'
    r=await client.get(url,timeout=25); r.raise_for_status()
    for j in r.json():
      cats=j.get('categories') or {}
      desc=' '.join([j.get('description',''),j.get('additional','')])
      yield {'source':'lever','external_id':str(j.get('id')),'title':j.get('text','Untitled'),'company':token,'location':cats.get('location',''),'url':j.get('hostedUrl',''),'description':re.sub('<[^>]+>',' ',desc),'posted_at':parse_job_date(j.get('createdAt'))}

def score_job(j,profile):
    text=(j['title']+' '+j['description']).lower(); score=0; reasons=[]
    roles=profile.get('role_families',[])
    hits=[x for x in roles if x.lower() in text]
    if hits: score+=30; reasons.append('Role family match: '+', '.join(hits[:3]))
    skills=['python','java','spring boot','spring ai','langchain','langgraph','llm','agentic','rag','kafka','react','angular','fastapi','multimodal','document ai','automation']
    sh=[x for x in skills if x in text]
    score+=min(30,len(sh)*4); 
    if sh: reasons.append('Relevant skills: '+', '.join(sh[:8]))
    loc=(j.get('location') or '').lower(); allowed=[x.lower() for x in profile.get('locations',[])]
    if any(a in loc for a in allowed) or 'remote' in loc: score+=20; reasons.append('Location preference match')
    if 'full-time' in text or 'full time' in text or 'full-time' in j.get('employment_type','').lower(): score+=10; reasons.append('Full-time signal')
    if j.get('posted_at'): 
      try:
        dt=datetime.fromisoformat(j['posted_at'].replace('Z','+00:00'))
        age=(datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).days
        if age<=1: score+=10; reasons.append('Updated within 24 hours')
        elif age<=7: score+=7; reasons.append('Updated within 7 days')
        elif age<=30: score+=3; reasons.append('Updated within 30 days')
      except: pass
    return min(100,score),reasons

@app.post('/api/discover')
async def discover():
    profile=get_profile();
    with connect() as c: src=[dict(r) for r in c.execute('SELECT * FROM sources WHERE active=1').fetchall()]
    added=0; errors=[]
    async with httpx.AsyncClient(headers={'User-Agent':'CareerOS/0.1 (personal job discovery)'}) as client:
      for s in src:
        if s['board_token']=='example': continue
        try:
          iterator=fetch_greenhouse(client,s['board_token']) if s['kind']=='greenhouse' else fetch_lever(client,s['board_token'])
          async for j in iterator:
            j['company']=s['name'] or j['company']; score,reasons=score_job(j,profile)
            with connect() as c:
              cur=c.execute('INSERT OR IGNORE INTO jobs(source,external_id,title,company,location,url,description,posted_at,score,score_reasons,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(j['source'],j['external_id'],j['title'],j['company'],j['location'],j['url'],j['description'],j['posted_at'],score,json.dumps(reasons),now()))
              if cur.rowcount: added+=1
        except Exception as e: errors.append(f"{s['name']}: {str(e)[:180]}")
    event('discovery',f'Discovery completed: {added} new jobs; {len(errors)} source errors')
    return {'new_jobs':added,'sources_checked':len(src),'errors':errors,'note':'Only configured public Greenhouse/Lever boards were checked. Add board tokens in Sources; this is not a universal LinkedIn search.'}
@app.get('/api/jobs')
def get_jobs(q:str='',minimum:int=0,limit:int=150):
    with connect() as c:
      rows=c.execute('SELECT * FROM jobs WHERE score>=? AND (title LIKE ? OR company LIKE ? OR description LIKE ?) ORDER BY score DESC, first_seen DESC LIMIT ?', (minimum,f'%{q}%',f'%{q}%',f'%{q}%',limit)).fetchall()
    out=[]
    for r in rows:
      d=dict(r); d['score_reasons']=json.loads(d['score_reasons']); out.append(d)
    return out
@app.post('/api/jobs/manual')
def manual_job(payload:dict):
    required=['title','company','url']
    if any(not payload.get(k) for k in required): raise HTTPException(400,'title, company and url are required')
    with connect() as c:
      cur=c.execute('INSERT OR IGNORE INTO jobs(source,external_id,title,company,location,url,description,posted_at,score,score_reasons,first_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?)',('manual',hashlib.sha1(payload['url'].encode()).hexdigest(),payload['title'],payload['company'],payload.get('location',''),payload['url'],payload.get('description',''),payload.get('posted_at'),0,'[]',now()))
    return {'ok':True,'id':cur.lastrowid}
@app.post('/api/applications')
def prepare_application(a:ApplicationIn):
    with connect() as c:
      if not c.execute('SELECT id FROM jobs WHERE id=?',(a.job_id,)).fetchone(): raise HTTPException(404,'Job not found')
      cur=c.execute('INSERT INTO applications(job_id,resume_version,answers,notes,status,created_at) VALUES(?,?,?,?,?,?)',(a.job_id,a.resume_version,json.dumps(a.answers),a.notes,'prepared',now()))
    event('application',f'Application package prepared for job #{a.job_id}')
    return {'id':cur.lastrowid,'status':'prepared','message':'Prepared only. No application has been submitted.'}
@app.get('/api/applications')
def get_applications():
    with connect() as c: rows=c.execute('SELECT a.*,j.title,j.company,j.url FROM applications a JOIN jobs j ON j.id=a.job_id ORDER BY a.created_at DESC').fetchall()
    out=[]
    for r in rows:
      d=dict(r); d['answers']=json.loads(d['answers']); out.append(d)
    return out
@app.post('/api/applications/{aid}/approve')
def approve_application(aid:int):
    with connect() as c:
      r=c.execute('SELECT id,status FROM applications WHERE id=?',(aid,)).fetchone()
      if not r: raise HTTPException(404,'Application not found')
      c.execute("UPDATE applications SET status='approved_to_submit',approved_at=? WHERE id=?",(now(),aid))
    event('approval',f'Application #{aid} approved by user; submission still requires the user to complete the employer site flow.')
    return {'ok':True,'status':'approved_to_submit','message':'Approval recorded. CareerOS has not submitted the application. Open the employer link and complete submission.'}
@app.post('/api/applications/{aid}/mark-submitted')
def mark_submitted(aid:int,payload:dict):
    if not payload.get('confirmation'): raise HTTPException(400,'Provide a confirmation note or reference from the employer site')
    with connect() as c:
      cur=c.execute("UPDATE applications SET status='submitted',submitted_at=? WHERE id=? AND status='approved_to_submit'",(now(),aid))
      if cur.rowcount==0: raise HTTPException(409,'Application must first be approved')
    event('application',f'Application #{aid} marked submitted by user confirmation: {payload["confirmation"][:150]}')
    return {'ok':True,'status':'submitted'}
@app.post('/api/outreach')
def create_outreach(o:OutreachIn):
    with connect() as c: cur=c.execute('INSERT INTO outreach(company,person,role,email,source_url,reason,subject,body,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(o.company,o.person,o.role,o.email,o.source_url,o.reason,o.subject,o.body,'draft',now()))
    return {'id':cur.lastrowid,'status':'draft'}
@app.get('/api/outreach')
def get_outreach():
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM outreach ORDER BY created_at DESC').fetchall()]
@app.post('/api/outreach/{oid}/approve')
def approve_outreach(oid:int):
    with connect() as c:
      cur=c.execute("UPDATE outreach SET status='approved_to_send',approved_at=? WHERE id=? AND status='draft'",(now(),oid))
      if not cur.rowcount: raise HTTPException(404,'Draft not found or no longer awaiting approval')
    return {'ok':True,'message':'Approval recorded. Copy and send the email yourself; no email was sent.'}
@app.get('/api/events')
def get_events():
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 30').fetchall()]
@app.get('/api/briefing')
def briefing():
    with connect() as c:
      counts={}
      for table in ['jobs','applications','outreach','projects','assets']:
        counts[table]=c.execute(f'SELECT COUNT(*) n FROM {table}').fetchone()['n']
      top=[dict(r) for r in c.execute('SELECT id,title,company,location,url,score,posted_at FROM jobs ORDER BY score DESC,first_seen DESC LIMIT 8').fetchall()]
      pending=c.execute("SELECT COUNT(*) n FROM applications WHERE status='prepared'").fetchone()['n']
      drafts=c.execute("SELECT COUNT(*) n FROM outreach WHERE status='draft'").fetchone()['n']
    return {'generated_at':now(),'counts':counts,'top_jobs':top,'pending_application_approvals':pending,'outreach_drafts_awaiting_review':drafts,'configuration':get_profile()}

if __name__=='__main__':
    import uvicorn
    uvicorn.run('backend.app:app',host='127.0.0.1',port=8765,reload=False)
