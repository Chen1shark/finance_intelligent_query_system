from curl_cffi import requests

url = "https://push2.eastmoney.com/api/qt/clist/get"
params = {
    "np": "1",
    "fltt": "1",
    "invt": "2",
    "cb": "jQuery123_123",
    "fs": "m:10+c:510050",
    "fields": "f12,f14",
    "fid": "f3",
    "pn": "1",
    "pz": "5",
    "po": "1",
    "dect": "1",
    "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    "wbp2u": "|0|0|0|web",
}

print("Testing with session (visit homepage first)...")
try:
    sess = requests.Session(impersonate="chrome")
    # Visit homepage first to establish cookies
    homepage = sess.get("https://quote.eastmoney.com/option/510050.html", timeout=10, verify=False)
    print(f"Homepage: status={homepage.status_code}")
    # Then request API
    resp = sess.get(url, params=params, timeout=20, verify=False)
    print(f"API: SUCCESS: status={resp.status_code}, len={len(resp.text)}")
    print(f"Preview: {resp.text[:200]}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

print("\nTesting curl_cffi without impersonation...")
try:
    resp = requests.get(url, params=params, timeout=20, verify=False)
    print(f"SUCCESS: status={resp.status_code}, len={len(resp.text)}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")

print("\nTesting with edge impersonation...")
try:
    resp = requests.get(url, params=params, timeout=20, verify=False, impersonate="edge101")
    print(f"SUCCESS: status={resp.status_code}, len={len(resp.text)}")
except Exception as e:
    print(f"FAILED: {type(e).__name__}: {e}")
