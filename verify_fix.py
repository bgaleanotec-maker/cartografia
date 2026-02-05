import urllib.request
import urllib.parse
import http.cookiejar

def verify():
    base_url = "http://127.0.0.1:5000"
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # 1. Login
    print(f"Logging in to {base_url}...")
    login_url = f"{base_url}/login"
    
    # Get CSRF if needed
    try:
        resp = opener.open(login_url)
        html = resp.read().decode('utf-8')
    except Exception as e:
        print(f"Failed to load login page: {e}")
        return

    csrf_token = None
    if 'name="csrf_token"' in html:
        try:
            # Rough extraction
            part = html.split('name="csrf_token"')[1]
            val_part = part.split('value="')[1]
            csrf_token = val_part.split('"')[0]
            print(f"Found CSRF token: {csrf_token}")
        except:
            print("Failed to extract CSRF token")

    data_dict = {
        'username': 'cartografo',
        'password': 'password'
    }
    if csrf_token:
        data_dict['csrf_token'] = csrf_token
        
    login_data = urllib.parse.urlencode(data_dict).encode('utf-8')

    try:
        # Check if we are redirected (successful login usually redirects)
        resp = opener.open(login_url, data=login_data)
        print(f"Login response code: {resp.getcode()}")
        print(f"Login response url: {resp.geturl()}")
    except Exception as e:
        print(f"Login POST failed: {e}")
        return

    # 2. Check Inbox
    print("Checking Cartography Inbox...")
    project_id = None
    try:
        resp = opener.open(f"{base_url}/cartography/inbox")
        content = resp.read().decode('utf-8')
        if resp.getcode() == 200:
            print("SUCCESS: Inbox loaded with 200 OK.")
            # Simple scrape for a project link: href="/cartography/project/(\d+)"
            import re
            match = re.search(r'/cartography/project/(\d+)', content)
            if match:
                project_id = match.group(1)
                print(f"Found project ID: {project_id}")
            else:
                print("No projects found in inbox to verify detail page.")
        else:
            print(f"FAILURE: Inbox returned {resp.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"FAILURE: Inbox returned {e.code}")
        print(e.read().decode('utf-8')[:500])

    # 3. Check Project Detail (if found)
    if project_id:
        print(f"Checking Project Detail (ID: {project_id})...")
        try:
            resp = opener.open(f"{base_url}/cartography/project/{project_id}")
            if resp.getcode() == 200:
                print("SUCCESS: Project Detail loaded with 200 OK.")
            else:
                print(f"FAILURE: Project Detail returned {resp.getcode()}")
        except urllib.error.HTTPError as e:
            print(f"FAILURE: Project Detail returned {e.code}")
            print(e.read().decode('utf-8')[:500])


if __name__ == "__main__":
    verify()
