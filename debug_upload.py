import urllib.request
import urllib.parse
import os

def test_upload():
    url = "http://127.0.0.1:5000/api/projects/2/upload"
    boundary = "boundary"
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }

    data = []
    data.append(f"--{boundary}".encode())
    data.append(b'Content-Disposition: form-data; name="file"; filename="test.txt"')
    data.append(b'Content-Type: text/plain')
    data.append(b'')
    data.append(b'Hello world content')
    data.append(f"--{boundary}--".encode())
    data.append(b'')
    
    body = b"\r\n".join(data)

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    
    print(f"Uploading to {url}...")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status Code: {response.getcode()}")
            print(f"Response: {response.read().decode()}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code}")
        print(f"Response: {e.read().decode()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upload()
