# Author: John Fitzgerald
# Title: reddit_collector.py
# Date Modified: 12/27/17
# Description: Leave script running to parse a subreddit's new posts, and insert them into a database.
# An email is sent out if the insert fails.
from bs4 import BeautifulSoup
from datetime import datetime
from email.mime import multipart, text
import requests
import re
import post
import pytz
import pyodbc
import sys
import getpass
import textwrap
import random
import time
import smtplib


class Post(object):
    def __init__(self, title, date_time, user, url):
        self.title = title
        self.date_time = date_time
        self.user = user
        self.url = url


class Reddit(object):
    def __init__(self, name):
        self.name = name
        self.comment_url =  "r/Seattle/comments/"
        self.url_regex = r"^https://reddit.com/r/([0-9A-Z]+)"

        self.sql_exists = textwrap.dedent("""SELECT * FROM Collector.guest.Posts WHERE datetime_posted = (?) and username = (?);""")
        self. sql_insert = textwrap.dedent("""
                INSERT INTO Collector.guest.Posts(datetime_added, datetime_posted, username, url_path, title)
                    VALUES (?, ?, ?, ?, ?);""")

        self.minutes = 60.0
        self.seconds = 60.0
        self.jitter = 0.17
        self.request_rate_small = float(self.minutes * (1.0 - self.jitter))
        self.request_rate_large = float(self.minutes * (1.0 + self.jitter))
        self.actual_request_rate = self.seconds * random.uniform(self.request_rate_small, self.request_rate_large)
        self.duplicate_factor = 0.5
        self.duplicate_count = 0
        self.insert_count = 0

        # TODO how to properly initialize an empty???
        self.div_classes = None
        self.duplicate_check = False

        self.email_messages = list()
        self.reddit = list()

    def set_tag(self, bs_obj):
        self.div_classes = bs_obj.find_all('div', attrs={'class': re.compile(r'thing$')})

    def loop_for_posts(self):
        title = date_time = user = url = "null"

        for i in range(0, len(self.div_classes)):
            line = str(self.div_classes[i])

            # pull relevant lines from HTML
            title_match = re.search(r'tabindex="1">(.+?)</a>', line)
            time_match = re.search(r'data-timestamp="(.+?)"', line)
            user_match = re.search(r'data-author="(.+?)"', line)
            url_match = re.search(r'href="(.+?)" rel="', line)

            # parse lines looking for regular expression matches
            if title_match:
                title = title_match.group(1)
            if time_match:
                date_time = time_match.group(1)
                date_time = datetime.utcfromtimestamp(int(date_time[:-3]))  # convert to UTC date time
                tz = pytz.timezone('America/Los_Angeles')
                # convert to Seattle time
                date_time = pytz.utc.localize(date_time, is_dst=None).astimezone(tz).replace(tzinfo=None)
            if user_match:
                user = user_match.group(1)
            if url_match:
                url = url_match.group(1)
                if self.comment_url in url:
                    url = "https://reddit.com" + url

            self.add(date_time, title, user, url)
            title = date_time = user = url = "null"

    def add(self, _date_time, _title, _user, _url):
        self.reddit.append(Post(_title, _date_time, _user, _url))

    def insert(self, start_time, cnxn, cursor):
        duplicate_check = False

        for count, entry in enumerate(self.reddit):
            insert_success = True
            cursor.execute(self.sql_exists, entry.date_time, entry.user)
            row = cursor.fetchall()

            # because r/Seattle/new orders postings by time, the first duplicate should trigger a break
            if len(row) >= 1:
                self.duplicate_count += 1
                print("[duplicate " + str(self.duplicate_count) + "] = " + str(row))

                # sleep for a quarter of the time to attempt a faster request
                elapsed = time.time() - start_time
                sleep_length = self.duplicate_factor * (self.actual_request_rate - elapsed)

                print("[sleep] = " + str(sleep_length))
                time.sleep(sleep_length)
                self.duplicate_check = True
                break
            else:
                # trigger email if the insert was unsuccessful
                try:
                    cursor.execute(self.sql_insert, datetime.now(), entry.date_time, entry.user, entry.url, entry.title)
                except pyodbc.DatabaseError as e:
                    insert_success = False
                    email_text = "title = " + entry.title + "\nposted = " + str(entry.date_time) + \
                                 "\nuser = " + entry.user + "\nurl = " + entry.url + \
                                 "\ncurrent time = " + str(datetime.now())
                    self.email_messages.append(email_text)
                    print("\n*****  [insert failed] = " + e.args[1] + "\n" + str(entry.date_time) +
                          "\n\t" + str(entry.title) + "\n\t" + entry.user + "\n\t" + entry.url + "\n")

                if insert_success is True:
                    self.insert_count += 1
                    print("[insert " + str(self.insert_count) + "] = " + str(datetime.now()) +
                          "\n\t" + entry.title + "\n" + entry.url)

            cnxn.commit()

    def finish(self):
        del self.reddit
        del self.email_messages
        self.reddit = self.email_messages = list()
        self.duplicate_check = False

    # def insert_posts(self):
    #
