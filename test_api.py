import urllib.request
import json
import urllib.error

base_url = "http://localhost:8000"

print("--- GET /health ---")
req = urllib.request.Request(f"{base_url}/health")
try:
    with urllib.request.urlopen(req) as response:
        print(json.dumps(json.loads(response.read().decode()), indent=2))
except Exception as e:
    print(e)

print("\n--- POST /audit/run_csv ---")
data = json.dumps({
    "csv_text": "Course_Code,Credits,Grade,Semester\nENG102,3,A,Spring 2022\nCSE115,4,A,Spring 2022\nMAT120,3,F,Spring 2022\nMAT120,3,B,Summer 2022",
    "program": "CSE"
}).encode('utf-8')

req = urllib.request.Request(f"{base_url}/audit/run_csv", data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print(json.dumps(json.loads(response.read().decode()), indent=2))
except urllib.error.HTTPError as e:
    print(f"HTTPError: {e.read().decode()}")
except Exception as e:
    print(e)
