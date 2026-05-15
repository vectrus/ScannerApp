"""Quick test script: reprocess all pages of test-boek-1 with Dutch OCR."""
import httpx

BASE = "http://127.0.0.1:8765"

httpx.post(f"{BASE}/api/projects/test-boek-1/open", timeout=15)
r = httpx.put(
    f"{BASE}/api/projects/test-boek-1/settings",
    json={"languages": ["nld", "eng"]},
    timeout=15,
)
print("Settings:", r.json()["settings"]["languages"])
print()
print("Reprocessing all pages...")
for page_id in ["03e70d47a60e", "885c06115db5", "b053dae60279"]:
    r = httpx.post(f"{BASE}/api/pages/{page_id}/reprocess", json={}, timeout=180)
    if r.status_code == 200:
        page = next((p for p in r.json() if p["id"] == page_id), None)
        if page:
            conf = page.get("avg_confidence")
            preview = (page.get("text_preview") or "")[:120]
            print(f"  {page_id}: has_ocr={page['has_ocr']} conf={conf}")
            print(f"    preview: {preview!r}")
    else:
        print(f"  {page_id}: ERROR {r.status_code}: {r.text[:200]}")
