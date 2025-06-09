FROM public.ecr.aws/lambda/python:3.11

RUN yum install -y unzip mesa-libGL libsndfile && yum clean all

ENV PYTHONUNBUFFERED=TRUE
ENV PIP_NO_CACHE_DIR=yes

WORKDIR /var/task

COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    rm -rf /root/.cache/pip

COPY lambda_function.py .
COPY model.pt .

COPY "BirdNET-Analyzer.zip" .
RUN unzip "BirdNET-Analyzer.zip" && pip install ./BirdNET-Analyzer && rm -rf BirdNET-Analyzer "BirdNET-Analyzer.zip"

CMD ["lambda_function.lambda_handler"]