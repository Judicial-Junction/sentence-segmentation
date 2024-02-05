import requests
import pandas as pd
from bs4 import BeautifulSoup
import re


def scrape(date):
    url = "https://dhccaseinfo.nic.in/jsearch/juddt1page.php?dc=31&fflag=1"
    data = {"juddt": date, "Submit": "Submit"}
    home = requests.post(
        url,
        headers={
            "Origin": "https://dhccaseinfo.nic.in",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=data,
    )

    table = BeautifulSoup(home.content, "html.parser")

    # page links
    page_links = table.find_all(class_="page_link")
    page_links
    base_url = "https://dhccaseinfo.nic.in"
    unique_links = set()
    for page_link in page_links:
        page_link_href = page_link.find("a", href=re.compile("/jsearch/"))
        if page_link_href is not None:
            page_link_full = base_url + page_link_href["href"]
            unique_links.add(page_link_full)

    unique_links.add(url)
    print(unique_links)

    global_df = pd.DataFrame()

    for pager in unique_links:
        url = pager
        home = requests.post(
            url,
            headers={
                "Origin": "https://dhccaseinfo.nic.in",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
        )

        table = BeautifulSoup(home.content, "html.parser")
        raw_case = []
        count = 0

        for row in table.find_all("tr"):
            count += 1
            row_data = []
            for cell in row.find_all("td"):
                link = cell.find("a", href=re.compile("downloadtext.php"))
                if link:
                    link_full = "https://dhccaseinfo.nic.in/jsearch/" + link["href"]
                    row_data.append(link_full)
                    continue
                row_data.append(cell.text)
            raw_case.append(row_data)

        df = pd.DataFrame(raw_case)
        if (df[1][1]) == " Information: No Matching record found":
            print(" Information: No Matching record found")
        else:
            pattern = r"\d+(?=[A-Za-z\s]*$)"
            records_total = int(re.findall(pattern, df[0][1])[0])

        year = date[-4:]
        end_pattern_case = year + ":DHC"

        df2 = df.iloc[3:, 1:4]

        df2.dropna(inplace=True)

        min_rows = min(len(df), len(df2))
        for i in range(min_rows):
            row = df.iloc[i]
            if row is not None:
                value = df2.iloc[i, 0]
                if value is not None:
                    index = value.find(end_pattern_case)
                    if index != -1:
                        df2.iloc[i, 0] = value[1:index]
        global_df = global_df._append(df2, ignore_index=True)

        if len(global_df) == records_total:
            print(f"Scrap for {date} complete")


scrape("14/09/2023")
