FROM python

RUN git clone https://github.com/cimc-raffles/docker-python-api.git /opt/app && \
    pip install -r /opt/app/requirements.txt

WORKDIR /opt

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
