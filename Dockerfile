FROM python:latest

WORKDIR /app

COPY requirements.txt .

RUN python3 -m pip install --no-cache-dir --upgrade -r requirements.txt

COPY . .

ENTRYPOINT ["python"]

CMD ["./app.py"]