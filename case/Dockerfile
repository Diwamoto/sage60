# case/ の Python を動かす: docker build -t sage60-case case && docker run --rm -v "$PWD":/w -w /w/case/trackball sage60-case python tb_collar.py
FROM python:3.14-slim
COPY requirements.txt requirements-debug.txt /tmp/
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r /tmp/requirements.txt -r /tmp/requirements-debug.txt
