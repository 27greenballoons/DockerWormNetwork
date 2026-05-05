FROM python:3.9-slim
RUN pip install --no-cache-dir docker pandas xgboost joblib scikit-learn
COPY detect.py /detect.py
CMD ["python3", "-u", "/detect.py"]
