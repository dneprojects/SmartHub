FROM python:3.11

COPY /src/requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# WORKDIR /
COPY /src /src
WORKDIR /src
CMD ["python3", "smarthub.py"]
