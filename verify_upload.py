import requests
import re
import os

BASE_URL = "http://127.0.0.1:5000"
SESSION = requests.Session()

def login():
    print("[*] Logging in...", flush=True)
    try:
        r = SESSION.get(f"{BASE_URL}/login")
        csrf_token = None
        if 'name="csrf_token"' in r.text:
            match = re.search(r'name="csrf_token" value="(.*?)"', r.text)
            if match:
                csrf_token = match.group(1)
        
        data = {'username': 'cartografo', 'password': 'password'}
        if csrf_token:
            data['csrf_token'] = csrf_token
            
        r = SESSION.post(f"{BASE_URL}/login", data=data)
        if r.status_code == 200 and "/cartography/inbox" in r.url:
            print("[+] Login successful", flush=True)
            return True
        elif r.status_code == 200: 
             # sometimes it doesn't redirect but logs in?
             print(f"[?] Login status 200, URL: {r.url}", flush=True)
             return True
        else:
            print(f"[-] Login failed: {r.status_code}", flush=True)
            return False
    except Exception as e:
        print(f"[-] Login exception: {e}", flush=True)
        return False

def create_project():
    print("[*] Creating test project...", flush=True)
    payload = {
        "name": "Test Upload Verify",
        "latitude": 4.0,
        "longitude": -74.0,
        "nodes": [],
        "description": "Auto-generated for verification"
    }
    r = SESSION.post(f"{BASE_URL}/api/visits/sync", json=payload)
    if r.status_code == 201:
        pid = r.json().get('project_id')
        print(f"[+] Project created with ID: {pid}", flush=True)
        return pid
    else:
        print(f"[-] Failed to create project: {r.text}", flush=True)
        return None

def test_uploads(project_id):
    print(f"[*] Testing uploads for Project {project_id}...", flush=True)
    
    # Create dummy file
    with open('dummy.txt', 'w') as f:
        f.write('test content')
        
    uploaded_ids = []
    
    # Upload 20 files
    for i in range(20):
        files = {'file': ('dummy.txt', open('dummy.txt', 'rb'))}
        r = SESSION.post(f"{BASE_URL}/api/projects/{project_id}/upload", files=files, data={'category': 'GENERAL'})
        if r.status_code == 201:
            uploaded_ids.append(r.json()['document']['id'])
            print(f"    [+] Upload {i+1}/20 success", flush=True)
        else:
            print(f"    [-] Upload {i+1} failed: {r.text}", flush=True)
            return False

    # Try 21st file
    print("[*] Attempting 21st upload (should fail)...", flush=True)
    files = {'file': ('dummy.txt', open('dummy.txt', 'rb'))}
    r = SESSION.post(f"{BASE_URL}/api/projects/{project_id}/upload", files=files, data={'category': 'GENERAL'})
    
    if r.status_code >= 400 and "Límite de 20 archivos" in r.text:
        print("[+] 21st upload failed as expected with correct message.", flush=True)
    else:
        print(f"[-] 21st upload UNEXPECTED result: {r.status_code} - {r.text}", flush=True)
        return False
        
    # Test Delete
    if uploaded_ids:
        doc_id = uploaded_ids[0]
        print(f"[*] Testing delete for Doc ID {doc_id}...", flush=True)
        r = SESSION.delete(f"{BASE_URL}/api/projects/documents/{doc_id}")
        if r.status_code == 200:
            print("[+] Delete successful", flush=True)
        else:
            print(f"[-] Delete failed: {r.text}", flush=True)
            return False
            
    # Cleanup dummy file
    os.remove('dummy.txt')
    return True

if __name__ == "__main__":
    if login():
        pid = create_project()
        if pid:
            test_uploads(pid)
