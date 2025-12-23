import hashlib, requests

user_id = "896533"
auth_code = "5RC14TENS6WK1ZJ2MFSI"
api_secret = "ryAoWHkIMpTizrK"

raw = f"{user_id}{auth_code}{api_secret}"
checksum = hashlib.sha256(raw.encode()).hexdigest()

url = "https://ant.aliceblueonline.com/rest/AliceBlueAPIService/sso/getUserDetails"
payload = {"checkSum": checksum}

resp = requests.post(url, json=payload, timeout=10)
print(resp.status_code, resp.text)
