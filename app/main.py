from typing import Union
from uvicorn.workers import UvicornWorker
from fastapi import FastAPI
from case_tokenization import segment

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/sentence-segmentation/{date}")
def segment(date: str):
    try:
        segment(date=date)
        return {"message": f"Data processing completed for {date}"}
    except Exception as e:
        return {"message": f"An error occurred: {str(e)}"}, 500
