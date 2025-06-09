###############################################
# Build container for AWS Lambda (Python 3.9) #
###############################################

FROM public.ecr.aws/lambda/python:3.9

RUN yum update -y && \
    yum install -y zip

RUN pip3 install --upgrade pip setuptools wheel && \
    pip3 install numpy opencv-python-headless -t /var/task/

# ONLY delete tests and cache, not full .py files
RUN rm -rf /var/task/numpy/__pycache__ \
           /var/task/numpy/*/tests \
           /var/task/numpy/tests \
           /var/task/numpy/f2py/tests

COPY lambda_function.py /var/task/

RUN cd /var/task && zip -r9 /tmp/lambda.zip .

