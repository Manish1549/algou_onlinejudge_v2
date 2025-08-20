FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app


COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
ENV DJANGO_SETTINGS_MODULE=onlineJudge.settings
ENV PYTHONUNBUFFERED=1

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]