import requests
from bs4 import BeautifulSoup
import pandas as pd 

url = "https://www.commbuys.com/bso/view/search/external/advancedSearchVendor.xhtml"
response = requests.get(url)
#print(response.text)

soup = BeautifulSoup(response.text,'html.parser')
titles = []
books = soup.find_all("td")
for book in books:
    titles.append(book.text)
df = pd.DataFrame({
    "title":titles
})
df.to_excel("books.xlsx",index=False)
print("saved data")
