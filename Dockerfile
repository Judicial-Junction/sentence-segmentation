FROM python:3.9

WORKDIR /app

ENV LANG             en
ENV SPACY_VERSION    2.3.5

COPY ./requirements.txt /app/requirements.txt

RUN pip install --upgrade pip --no-cache-dir \
    && pip install -r requirements.txt --no-cache-dir \
    && pip install gunicorn \
    && pip install spacy==${SPACY_VERSION}

RUN python3 -m spacy download en

COPY ./app /app

CMD ["gunicorn", "main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8100"]


EXPOSE 8100
