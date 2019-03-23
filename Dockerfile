FROM python:3-alpine
RUN pip install BeautifulSoup4 requests matrix_client
RUN mkdir /app
COPY . /app
CMD ["python","/app/src/matrix-bot.py"]
