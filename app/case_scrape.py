import requests
import pandas as pd
from bs4 import BeautifulSoup
import re
import datetime
import os
import boto3


def scrape(date):
    # ctx = ssl.create_default_context()
    # ctx.check_hostname = False
    # ctx.verify_mode = ssl.CERT_NONE

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

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
            formatted_date = datetime.datetime.strptime(date, "%d/%m/%Y").strftime(
                "%Y%m%d"
            )
            print(f"Scrap for {date} complete")
            global_df["body_content"] = None
            directory = f"cases/date={formatted_date}"
            os.makedirs(directory, exist_ok=True)

            for i in range(len(global_df)):
                # response = urlopen(global_df.iloc[i, 1], context=ctx)
                response = requests.get(global_df.iloc[i, 1])
                data_soup = BeautifulSoup(response.content, "html.parser")
                body_content = data_soup
                print(global_df.iloc[i, 1])
                case = global_df.iloc[i, 0]
                cleaned_name = re.sub(r"[^\w\s]", "", case)
                cleaned_name = cleaned_name.replace(" ", "_")

                print(case)
                output_directory = f"Cases/date={formatted_date}/{cleaned_name}.txt"
                text = body_content.get_text()
                if text.startswith("$"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:])

                s3.put_object(
                    Bucket="digital-adhivakta",
                    Key=output_directory,
                    Body=text.encode("utf-8"),
                )
                print(f"Text content saved to S3 bucket with key: {output_directory}")

                # print(body_content)


scrape("14/09/2023")
