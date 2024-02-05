from sentence_transformers import SentenceTransformer
import spacy
import pandas as pd
import boto3
from io import StringIO
import datetime
import os


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
