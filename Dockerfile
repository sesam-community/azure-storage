FROM python:3-slim
MAINTAINER Graham Moore "graham.moore@sesam.io"
COPY ./service/*.py /service/
COPY ./service/requirements.txt /service/requirements.txt
WORKDIR /service
RUN pip install --upgrade pip \
  && pip install -r requirements.txt

EXPOSE 5000/tcp
ENTRYPOINT ["python"]
CMD ["proxy-service.py"]
