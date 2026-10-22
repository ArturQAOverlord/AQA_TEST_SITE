# Образ с Python, Playwright и браузерами — версия должна совпадать с playwright из requirements.txt
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /lab
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LAB_HOST=0.0.0.0 \
    LAB_PORT=5000 \
    LAB_DEBUG=0 \
    PYTHONUNBUFFERED=1

EXPOSE 5000
CMD ["python", "app.py"]
