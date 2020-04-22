FROM webmon:test

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY src ./src

EXPOSE 8080

CMD python ./src/test.py



