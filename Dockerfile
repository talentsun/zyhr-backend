FROM python:3.6

WORKDIR /src
COPY ./requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt

VOLUME /var/lib/hwbackend

COPY . /src
EXPOSE 8000
CMD sh launch.sh

