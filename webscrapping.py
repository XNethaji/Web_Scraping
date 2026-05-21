from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import datetime

start_time = time.time()
start_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"─────────────────────────────────────")
print(f"🕐 Scraping started at : {start_datetime}")
print(f"─────────────────────────────────────")



options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 15)


url = "https://www.commbuys.com/bso/view/search/external/advancedSearchVendor.xhtml"
driver.get(url)
time.sleep(3)


country_dropdown = wait.until(EC.presence_of_element_located((
    By.ID, "vendorSearchForm:country"
)))
select = Select(country_dropdown)
select.select_by_visible_text("United States of America")
print("✅ Country selected: United States of America")
time.sleep(2)


search_btn = wait.until(EC.element_to_be_clickable((
    By.ID, "vendorSearchForm:btnVendorSearch"
)))
search_btn.click()
print("✅ Search button clicked!")
time.sleep(4)


all_vendors = []
page = 1

while True:
    page_start = time.time() 
    print(f"\n📄 Scraping page {page}...")


    print(f"Scraping page {page}...")

   
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        time.sleep(2)
    except:
        print("⚠️ Table not found on this page")
        break


    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    print(f"   Found {len(rows)} rows on page {page}")
    
   

    for row in rows:
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) >= 8:
            all_vendors.append({
                "Vendor ID":    cols[0].text.strip(),   # col[0] = Vendor ID
                "Vendor Name":  cols[2].text.strip(),   # col[2] = Vendor Name
                "Address":      cols[3].text.strip(),   # col[3] = Address
                "City":         cols[4].text.strip(),   # col[4] = City
                "State":        cols[5].text.strip(),   # col[5] = State
                "Postal Code":  cols[6].text.strip(),   
                "Contact Name": cols[7].text.strip(),   
                "Phone":        cols[8].text.strip() if len(cols) > 8 else "",  # col[8] = Phone
            })

   
    page_end = time.time()
    page_time = round(page_end - page_start, 2)
    print(f"   ✅ Rows on page      : {len(rows)}")
    print(f"   ✅ Total vendors     : {len(all_vendors)}")
    print(f"   ⏱️  Page load time    : {page_time}s")
    print(f"   🕐 Current time      : {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"   → Total vendors so far: {len(all_vendors)}")

 
    try:
        next_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, "//a[@title='Next Page'] | //li[contains(@class,'next')]/a | //a[contains(@class,'next')]"
        )))
        next_btn.click()
        page += 1
        time.sleep(3)
    except:
        print(f"✅ Last page reached. Total pages scraped: {page}")
        break


df = pd.DataFrame(all_vendors)
df.drop_duplicates(inplace=True)
df.to_excel("usa_vendors.xlsx", index=False)

print(f"\n✅ Done! {len(df)} USA vendors saved to usa_vendors.xlsx")


end_time = time.time()
end_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
total_seconds = end_time - start_time

hours   = int(total_seconds // 3600)
minutes = int((total_seconds % 3600) // 60)
seconds = int(total_seconds % 60)

print(f"\n─────────────────────────────────────")
print(f"🕐 Started  at         : {start_datetime}")
print(f"🕑 Finished at         : {end_datetime}")
print(f"⏱️  Total Time Taken    : {hours}h {minutes}m {seconds}s")
print(f"📦 Total Vendors Saved : {len(df)}")
print(f"📄 Total Pages Scraped : {page}")
print(f"─────────────────────────────────────")
driver.quit()