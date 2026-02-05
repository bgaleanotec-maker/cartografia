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
        if r.status_code == 200:
            return True
        return False
    except Exception as e:
        print(f"[-] Login error: {e}", flush=True)
        return False

def verify_persistence():
    # 1. Create Project
    print("[*] Creating project...", flush=True)
    try:
        r = SESSION.post(f"{BASE_URL}/api/visits/sync", json={
            "name": "Persistence Test",
            "latitude": 0, "longitude": 0, "nodes": []
        })
        if r.status_code != 201:
            print(f"[-] Failed create: {r.status_code}", flush=True)
            return
        pid = r.json()['project_id']
        
        # 2. Upload File
        print(f"[*] Uploading file to Project {pid}...", flush=True)
        with open('persist_test.txt', 'w') as f: f.write('persist content')
        
        with open('persist_test.txt', 'rb') as f:
            files = {'file': ('persist_test.txt', f)}
            r = SESSION.post(f"{BASE_URL}/api/projects/{pid}/upload", files=files, data={'category': 'EVIDENCIA'})
        
        if r.status_code != 201:
            print(f"[-] Upload failed: {r.status_code}", flush=True)
            return
            
        # 3. Request Page HTML (Reload)
        print("[*] Reloading page (GET request)...", flush=True)
        r = SESSION.get(f"{BASE_URL}/cartography/project/{pid}")
        
        # 4. Check if file is in the HTML/JS
        if 'persist_test.txt' in r.text:
            print("[SUCCESS] File found in page HTML after reload.", flush=True)
        else:
            print("[FAILURE] File NOT found in page HTML after reload.", flush=True)
            
    finally:
        if os.path.exists('persist_test.txt'):
            try:
                os.remove('persist_test.txt')
            except:
                pass

if __name__ == "__main__":
    if login():
        verify_persistence()
