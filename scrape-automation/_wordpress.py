import requests
from bs4 import BeautifulSoup
import json

BASE = "https://iba-world.com"
START = "https://iba-world.com/cocktails/all-cocktails/"

session = requests.Session()

session.headers = {
    "User-Agent": "Mozilla/5.0"
}

session.verify = False


def get_pages():

    r = session.get(START)
    soup = BeautifulSoup(r.text, "html.parser")

    nums = []

    for el in soup.select(".page-numbers"):
        t = el.text.strip()

        if t.isdigit():
            nums.append(int(t))

    last = max(nums)

    pages = [START]

    for i in range(2, last + 1):
        pages.append(f"{START}page/{i}/")

    return pages


def get_links(url):

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    links = []

    for c in soup.select(".cocktail a"):
        links.append(c["href"])

    return links


def parse_recipe(soup):

    ingredients = []
    method = ""
    garnish = ""

    for h in soup.find_all("h4"):

        title = h.text.strip().lower()

        if title == "ingredients":

            ul = h.find_next("ul")

            if ul:
                ingredients = [
                    li.text.strip()
                    for li in ul.find_all("li")
                ]

        elif title == "method":

            ps = h.find_next("div").find_all("p")

            method = " ".join(
                p.text.strip()
                for p in ps
            )

        elif title == "garnish":

            p = h.find_next("p")

            if p:
                garnish = p.text.strip()

    return ingredients, method, garnish


def scrape_detail(url):

    r = session.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    name = soup.select_one("h1").text.strip()

    ingredients, method, garnish = parse_recipe(soup)

    return {
        "name": name,
        "ingredients": ingredients,
        "method": method,
        "garnish": garnish,
        "url": url
    }


pages = get_pages()

print("pages:", len(pages))

links = []

for p in pages:
    links.extend(get_links(p))

print("cocktails:", len(links))


data = []

for i, link in enumerate(links):

    print(i + 1, link)

    try:
        data.append(scrape_detail(link))
    except:
        pass


print("TOTAL:", len(data))


with open("cocktails.json", "w", encoding="utf8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)