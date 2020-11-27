FROM python:3.8

RUN git clone https://github.com/j6k4m8/goosepaper
WORKDIR /goosepaper
RUN pip3 install -r ./requirements.txt
RUN pip3 install -e .
