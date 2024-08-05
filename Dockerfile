FROM public.ecr.aws/docker/library/python:3.10-slim-bookworm

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip3 install -r requirements.txt

COPY /src .

ENTRYPOINT [ "python3", "-u" , "/app/exporter.py"]