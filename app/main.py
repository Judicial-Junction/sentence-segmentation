from typing import Union
from uvicorn.workers import UvicornWorker
from fastapi import FastAPI
import requests

# from case_tokenization import segment
from bs4 import BeautifulSoup
import spacy
import re
import pandas as pd
import boto3
from io import StringIO
import datetime
import os
# import dotenv

# dotenv.load_dotenv('../.env')

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/sentence-segmentation/{date}")
def segment(date: str):
    try:
        scrape(date=date)
        segment(date=date)
        return {"message": f"Data processing completed for {date}"}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500


def scrape(date):
    # ctx = ssl.create_default_context()
    # ctx.check_hostname = False
    # ctx.verify_mode = ssl.CERT_NONE

    formatted_date = datetime.datetime.strptime(date, "%Y%m%d")
    date = formatted_date.strftime("%d/%m/%Y")
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


def segment(date: str):
    nlp = spacy.load("en_core_web_sm")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    s3_view = boto3.resource(
        "s3",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )

    s3_bucket = "digital-adhivakta"
    prefix = "Cases/date="

    default = (datetime.datetime.now() - datetime.timedelta(days=3)).strftime("%Y%m%d")
    date_formatted = datetime.datetime.strptime(date or default, "%Y%m%d").strftime(
        "%Y%m%d"
    )

    prefix = prefix + date_formatted
    response = s3.list_objects_v2(Bucket=s3_bucket, Prefix=prefix)

    files = response.get("Contents", [])
    cases = []
    for file in files:
        file_key = file.get("Key")
        if file_key.endswith(".txt"):
            cases.append(file_key)

    case_data = []

    for case in cases:
        case_content = (
            s3_view.Object(s3_bucket, case).get()["Body"].read().decode("utf-8")
        )
        doc = nlp(case_content)

        sentences = [sent.text for sent in doc.sents]

        case_data.append(
            {
                "case_no": case,
                "datedate_of_judgement": date_formatted,
                "tokens": sentences,
            }
        )

    case_df = pd.DataFrame(case_data)
    case_buffer = StringIO()
    case_csv = case_df.to_csv(case_buffer, index=False)
    case_buffer.seek(0)

    s3.put_object(
        Body=case_buffer.getvalue(),
        Bucket=s3_bucket,
        Key=f"Tokens/date_{date_formatted}.csv",
    )
