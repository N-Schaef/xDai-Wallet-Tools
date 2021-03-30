FROM python:3-alpine
ENV PYTHONUNBUFFERED=1
ADD . /api
WORKDIR /api 
RUN apk --no-cache add mariadb-client mariadb-dev gcc python3-dev musl-dev libffi-dev mariadb-connector-c-dev
RUN pip install -r requirements.txt
RUN pip install uwsgi mysql-connector-python
RUN apk --no-cache del mariadb-dev python3-dev
ENV PORT=8000
EXPOSE 8000
CMD ["/api/runner.sh"]
