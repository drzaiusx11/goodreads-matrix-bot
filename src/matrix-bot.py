import traceback
import re
import requests
import os
import logging
from time import sleep
from bs4 import BeautifulSoup
from matrix_client.client import MatrixClient
from matrix_client.api import MatrixRequestError

logger = logging.getLogger("goodreads-matrix-bot")

USERNAME = os.environ['USERNAME']
PASSWORD = os.environ['PASSWORD']
SERVER = os.environ['SERVER']

class MatrixBot:

    def connect(self):
        try:
            logger.info("connecting to {}".format(self.server))
            self.client = MatrixClient(self.server)
            self.client.login_with_password(self.username, self.password)
            logger.info("connection established")

            # Store empty list of handlers
            self.handlers = []

            # listen for invites and automatically accept them
            self.client.add_invite_listener(self.handle_invite)
            self.rooms = []

            # Add all rooms we're currently in to self.rooms and add their callbacks
            for room_id, room in self.client.get_rooms().items():
                room.add_listener(self.handle_message)
       	        self.rooms.append(room_id)

        except Exception:
            logger.warning(
                "connection to {} failed".format(self.server) +
                ", retrying in 5 seconds...")
            sleep(5)
            self.connect()

    # username - Matrix username
    # password - Matrix password
    # server   - Matrix server url : port
    # rooms    - List of rooms ids to operate in, or None to accept all rooms
    def __init__(self, username, password, server, rooms=None):
        self.username = username
        self.password = password
        self.server = server
        self.rooms = rooms

        self.connect()

    def add_handler(self, handler):
        self.handlers.append(handler)

    def handle_message(self, room, event):
        # Make sure we didn't send this message
        if re.match("@" + self.username, event['sender']):
            return

        try:
            if event['type'] == "m.room.message":
                rx_msg = event['content']['body']
                if re.search(r"#book", rx_msg):
                    book_url = self.get_book_url(rx_msg)
                    print('found book: '+book_url)
                    if (book_url):
                        img_info = self.get_book_img(book_url)
                        img = requests.get(img_info['url'])
                        mxc_url = self.client.upload(img.content, 'image/jpeg')
                        #html = "<a href='"+book_url+"'><img src='"+mxc_url+"'/></a>"
                        #print(html)
                        room.send_image(mxc_url, img_info['title'])
                        room.send_text(book_url)
        except (TypeError):
            pass

    def handle_invite(self, room_id, state):
        print("Got invite to room: " + str(room_id))
        print("Joining...")
        room = self.client.join_room(room_id)

        # Add message callback for this room
        room.add_listener(self.handle_message)

        print("Joined!")

        # Add room to list
        self.rooms.append(room)

    def get_book_url(self, search_string):
        search_words = search_string.split()
        filtered_search_words = filter(lambda w: not re.search(r"#book", w), search_words)
        query = '+'.join(filtered_search_words)
        page = requests.get("https://www.goodreads.com/search?q="+query)
        soup = BeautifulSoup(page.content, 'html.parser')
        results = soup.find_all('a', class_='bookTitle')
        if (len(results) == 0):
            return None
        url = 'https://goodreads.com' + results[0]['href'].split('-')[0].split('.')[0]
        return url

    def get_book_img(self, book_url):
        page = requests.get(book_url)
        soup = BeautifulSoup(page.content, 'html.parser')
        img_tag = soup.find("img", {"id": "coverImage"})
        h1_tag = soup.find("h1", {"id": "bookTitle"})
        return { 'title': h1_tag.text, 'url': img_tag['src'] }

    def start_polling(self):
        # Starts polling for messages
        self.client.start_listener_thread(
	    exception_handler=lambda e: self.connect())
        return self.client.sync_thread

def main():
    # Create an instance of the MatrixBotAPI
    bot = MatrixBot(USERNAME, PASSWORD, SERVER)

    # Start polling
    bot.start_polling()

    # Infinitely read stdin to stall main thread while the bot runs in other threads
    while True:
        sleep(1)

if __name__ == "__main__":
    main()
