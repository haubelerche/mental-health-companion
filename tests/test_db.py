import sys
import os
sys.path.insert(0, os.getcwd())

import httpx
from scripts.config import SUPABASE_URL, SUPABASE_PROJECT_ID, SUPABASE_SECRET
from src.database import get_client

print(f"[+] URL: {SUPABASE_URL}")
print(f"[+] Project ID: {SUPABASE_PROJECT_ID}")

# Ping REST API health endpoint
health_url = f"{SUPABASE_URL}/rest/v1/"
headers = {
    "apikey": SUPABASE_SECRET,
    "Authorization": f"Bearer {SUPABASE_SECRET}",
}
resp = httpx.get(health_url, headers=headers, timeout=10)
print(f"[+] REST API status: {resp.status_code}")
assert resp.status_code in (200, 404), f"Unexpected status: {resp.status_code}"

# Khoi tao client singleton
client = get_client()
print(f"[+] Supabase client: OK")
print(f"[+] KET NOI SUPABASE THANH CONG!")

