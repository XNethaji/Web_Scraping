import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
import warnings
import pandas as pd
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ─────────────────────────────────────────
# LOG: Start Time
# ─────────────────────────────────────────
start_time = time.time()
start_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"─────────────────────────────────────────")
print(f"🕐 Scraping started at : {start_datetime}")
print(f"─────────────────────────────────────────")

# ─────────────────────────────────────────
# STEP 1: Setup Session
# ─────────────────────────────────────────
session = requests.Session()
base_url = "https://www.commbuys.com/bso/view/search/external/advancedSearchVendor.xhtml"

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-language": "en-GB,en;q=0.7",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
}

ajax_headers = {
    "accept": "application/xml, text/xml, */*; q=0.01",
    "accept-language": "en-GB,en;q=0.7",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "faces-request": "partial/ajax",
    "origin": "https://www.commbuys.com",
    "referer": base_url,
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

# ─────────────────────────────────────────
# STEP 2: Load page → get cookies + ViewState
# ─────────────────────────────────────────
print("🌐 Loading website...")
response = session.get(base_url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

view_state = soup.find("input", {"name": "javax.faces.ViewState"})
view_state_value = view_state["value"] if view_state else ""
csrf_token = session.cookies.get("XSRF-TOKEN", "")
print(f"✅ ViewState   : {view_state_value[:40]}...")
print(f"✅ CSRF Token  : {csrf_token[:20]}...")

# ─────────────────────────────────────────
# STEP 3: Submit Search → get page 1
# ─────────────────────────────────────────
print("\n🔍 Submitting search for USA vendors...")

search_payload = {
    "javax.faces.partial.ajax":    "true",
    "javax.faces.source":          "vendorSearchForm:j_idt311",
    "javax.faces.partial.execute": "@all",
    "javax.faces.partial.render":  "advSearchFormFields advSearchResults advancedSearchMainPanelContainer",
    "vendorSearchForm:j_idt311":   "vendorSearchForm:j_idt311",
    "vendorSearchForm":            "vendorSearchForm",
    "_csrf":                       csrf_token,
    "vendorSearchForm:vendorName":            "",
    "vendorSearchForm:vendorAltName":         "",
    "vendorSearchForm:vendorId":              "",
    "vendorSearchForm:alternateId":           "",
    "vendorSearchForm:city":                  "",
    "vendorSearchForm:country":               "US",
    "vendorSearchForm:zip":                   "",
    "vendorSearchForm:county":                "",
    "vendorSearchForm:state":                 "",
    "vendorSearchForm:classId":               "",
    "vendorSearchForm:classItemId":           "",
    "vendorSearchForm:itemDescription":       "",
    "vendorSearchForm:searchScopeType_input": "false",
    "javax.faces.ViewState":       view_state_value,
}

search_response = session.post(base_url, headers=ajax_headers, data=search_payload)
print(f"✅ Search submitted — Status: {search_response.status_code}")

# Update ViewState
try:
    xml_s = BeautifulSoup(search_response.text, features="xml")
    vs = xml_s.find("update", {"id": lambda x: x and "ViewState" in x})
    if vs:
        view_state_value = vs.get_text(strip=True)
        print(f"✅ ViewState updated: {view_state_value[:40]}...")
except:
    pass

# ─────────────────────────────────────────
# STEP 4: Extract vendors function
# ─────────────────────────────────────────
def extract_vendors(xml_text):
    vendors = []
    try:
        xml_soup = BeautifulSoup(xml_text, features="xml")
        updates = xml_soup.find_all("update")
        html_content = ""
        for update in updates:
            html_content += update.get_text()

        html_soup = BeautifulSoup(html_content, "html.parser")

        # Find rows by data-ri attribute (works for all pages)
        rows = html_soup.find_all("tr", {"data-ri": True})

        if not rows:
            rows = html_soup.find_all("tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 7:
                link = cols[0].find("a")
                vendor_id = link.get_text(strip=True) if link else cols[0].get_text(strip=True)

                if not vendor_id or not any(c.isdigit() for c in vendor_id):
                    continue

                vendors.append({
                    "Vendor ID":    vendor_id,
                    "Vendor Name":  cols[2].get_text(strip=True),
                    "Address":      cols[3].get_text(strip=True),
                    "City":         cols[4].get_text(strip=True),
                    "State":        cols[5].get_text(strip=True),
                    "Postal Code":  cols[6].get_text(strip=True),
                    "Contact Name": cols[7].get_text(strip=True) if len(cols) > 7 else "",
                    "Phone":        cols[8].get_text(strip=True) if len(cols) > 8 else "",
                })
    except Exception as e:
        print(f"   ❌ Parse error: {e}")
    return vendors

# Extract page 1
first_page_vendors = extract_vendors(search_response.text)
print(f"✅ Page 1 vendors found: {len(first_page_vendors)}")

# ─────────────────────────────────────────
# STEP 5: Parallel fetch function
# ─────────────────────────────────────────
lock = threading.Lock()

def fetch_page(page_num):
    try:
        # Each thread creates its own session
        thread_session = requests.Session()

        # Copy cookies from main session
        thread_session.cookies.update(session.cookies)

        payload = {
            "javax.faces.partial.ajax":    "true",
            "javax.faces.source":          "vendorSearchResultsForm:vendorResultId",
            "javax.faces.partial.execute": "vendorSearchResultsForm:vendorResultId",
            "javax.faces.partial.render":  "vendorSearchResultsForm:vendorResultId",
            "vendorSearchResultsForm:vendorResultId_pagination":    "true",
            "vendorSearchResultsForm:vendorResultId_first":         str((page_num - 1) * 25),
            "vendorSearchResultsForm:vendorResultId_rows":          "25",
            "vendorSearchResultsForm:vendorResultId_encodeFeature": "true",
            "vendorSearchResultsForm":     "vendorSearchResultsForm",
            "_csrf":                       csrf_token,
            "javax.faces.ViewState":       view_state_value,
        }

        resp = thread_session.post(base_url, headers=ajax_headers, data=payload, timeout=15)
        vendors = extract_vendors(resp.text)
        return page_num, vendors

    except Exception as e:
        print(f"   ❌ Page {page_num} error: {e}")
        return page_num, []

# ─────────────────────────────────────────
# STEP 6: Parallel Scraping
# ─────────────────────────────────────────
TOTAL_PAGES = 2285
THREADS = 8       # 10 pages at the same time
BATCH_SIZE = 50      # save every 50 pages

all_vendors = first_page_vendors.copy()
pages_list = list(range(2, TOTAL_PAGES + 1))

print(f"\n🚀 Starting parallel scraping — {THREADS} threads...")
print(f"📋 Total pages: {TOTAL_PAGES} | Batch save every: {BATCH_SIZE} pages")
print(f"─────────────────────────────────────────")

batch_start = time.time()
completed = 0
failed_pages = []

with ThreadPoolExecutor(max_workers=THREADS) as executor:
    # Submit all pages
    future_to_page = {executor.submit(fetch_page, p): p for p in pages_list}

    for future in as_completed(future_to_page):
        page_num, vendors = future.result()
        completed += 1

        if vendors:
            with lock:
                all_vendors.extend(vendors)
            print(f"📄 Page {page_num:4d} | Vendors: {len(vendors):2d} | Total: {len(all_vendors):6d} | Done: {completed}/{TOTAL_PAGES-1}")
        else:
            failed_pages.append(page_num)
            print(f"⚠️  Page {page_num:4d} | No data | Done: {completed}/{TOTAL_PAGES-1}")

        # Auto save every BATCH_SIZE pages
        if completed % BATCH_SIZE == 0:
            with lock:
                df_temp = pd.DataFrame(all_vendors)
                df_temp.drop_duplicates(inplace=True)
                df_temp.to_excel("usa_vendors_fast.xlsx", index=False)
            elapsed = round(time.time() - batch_start, 1)
            print(f"   💾 Auto-saved {len(all_vendors)} vendors | Elapsed: {elapsed}s")
            batch_start = time.time()

# ─────────────────────────────────────────
# STEP 7: Retry failed pages
# ─────────────────────────────────────────
if failed_pages:
    print(f"\n🔄 Retrying {len(failed_pages)} failed pages...")
    for page_num in failed_pages:
        _, vendors = fetch_page(page_num)
        if vendors:
            all_vendors.extend(vendors)
            print(f"   ✅ Page {page_num} recovered — {len(vendors)} vendors")
        else:
            print(f"   ❌ Page {page_num} failed again — skipping")
        time.sleep(0.5)

# ─────────────────────────────────────────
# STEP 8: Save Final Excel
# ─────────────────────────────────────────
df = pd.DataFrame(all_vendors)
df.drop_duplicates(inplace=True)
df.sort_values("Vendor ID", inplace=True)
df.to_excel("usa_vendors_fast.xlsx", index=False)

# ─────────────────────────────────────────
# LOG: Final Summary
# ─────────────────────────────────────────
end_time = time.time()
end_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total_seconds = end_time - start_time
hours   = int(total_seconds // 3600)
minutes = int((total_seconds % 3600) // 60)
seconds = int(total_seconds % 60)

print(f"\n─────────────────────────────────────────")
print(f"🕐 Started  at          : {start_datetime}")
print(f"🕑 Finished at          : {end_datetime}")
print(f"⏱️  Total Time Taken     : {hours}h {minutes}m {seconds}s")
print(f"📦 Total Vendors Saved  : {len(df)}")
print(f"📄 Total Pages Scraped  : {TOTAL_PAGES}")
print(f"❌ Failed Pages         : {len(failed_pages)}")
print(f"─────────────────────────────────────────")