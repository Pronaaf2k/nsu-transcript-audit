import os

os.environ['TEST_MODE'] = 'true'

from fastapi.testclient import TestClient

from packages.api.main import app


client = TestClient(app)
AUTH = {'Authorization': 'Bearer test-token'}


def test_health_endpoint():
    res = client.get('/health')
    assert res.status_code == 200
    body = res.json()
    assert body['status'] == 'ok'
    assert body['ocr'] == 'gemini'
    assert 'gemini_configured' in body


def test_programs_endpoint_returns_supported_codes():
    res = client.get('/programs')
    assert res.status_code == 200
    programs = res.json()['programs']
    codes = {p['code'] for p in programs}
    assert {'CSE', 'BBA', 'ETE', 'ENV', 'ENG', 'ECO'}.issubset(codes)


def test_program_details_endpoint():
    res = client.get('/programs/CSE')
    assert res.status_code == 200
    body = res.json()
    assert body['program'] == 'CSE'
    assert body['program_name'] == 'Computer Science & Engineering'
    assert body['total_credits_required'] > 0


def test_program_alias_normalization():
    res = client.get('/programs/EEE')
    assert res.status_code == 200
    body = res.json()
    assert body['program'] == 'ETE'


def test_audit_run_csv_returns_expected_shape():
    csv_text = (
        'Course_Code,Course_Name,Credits,Grade,Semester\n'
        'CSE115,Programming Language I,3,A,Spring 2020\n'
        'MAT120,Calculus I,3,B+,Spring 2020\n'
        'ENG102,English Composition,3,A-,Summer 2020\n'
    )
    res = client.post('/audit/run_csv', json={'csv_text': csv_text, 'program': 'CSE'}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body['program'] == 'CSE'
    assert 'audit_result' in body
    assert 'graduation_status' in body


def test_audit_run_csv_accepts_program_alias():
    csv_text = (
        'Course_Code,Course_Name,Credits,Grade,Semester\n'
        'ETE131,Circuits I,3,A,Spring 2020\n'
    )
    res = client.post('/audit/run_csv', json={'csv_text': csv_text, 'program': 'EEE'}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body['program'] == 'ETE'
