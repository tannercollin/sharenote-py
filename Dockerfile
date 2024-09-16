FROM python:3.11-bookworm

WORKDIR /sharenote-py

COPY requirements.txt gunicorn.conf.py main.py ./

COPY assets ./assets

RUN pip install -r requirements.txt

COPY settings.py .

CMD ["gunicorn", "main:flask_app"]
