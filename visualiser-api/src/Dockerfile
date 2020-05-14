FROM python:3.7
MAINTAINER Robbie Anderson hello@robbiea.co.uk

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ENV EVENTS_SOURCE_STORE=metaflow-events-store
ENV EVENTS_SOURCE_INDEX=metaflow-events-store-index
EXPOSE 80

COPY *.py ./

USER server
COPY ~/.aws/credentials ~/.aws/credentials 

CMD python server.py