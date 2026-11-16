from fastapi.testclient import TestClient
from backend.app import app, init_db
init_db()
client=TestClient(app)
def test_health(): assert client.get('/api/health').status_code==200
def test_profile_defaults():
    p=client.get('/api/profile').json()
    assert p['salary_min_lpa']==15 and p['salary_max_lpa']==18
    assert p['briefing_time']=='09:00'
def test_projects_seeded(): assert len(client.get('/api/projects').json())>=1
