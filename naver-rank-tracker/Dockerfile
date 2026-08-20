FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 데이터는 볼륨(/data)에 — 컨테이너 재배포에도 이력 유지
ENV RANKTRACKER_DB=/data/rank_tracker.db \
    HOST=0.0.0.0 \
    PORT=8000
VOLUME /data
EXPOSE 8000

CMD ["python", "main.py"]
