# Author: John Fitzgerald
# Title: weather.py
# Date Modified: 1/10/18
# Description: Leave script running to parse weather.com, and insert weather into a database.
# An email is sent out if the insert fails.
from datetime import datetime, timedelta
import time
import re
import pyodbc
import textwrap
import random


class Post(object):
    def __init__(self, date_time, temp, wind, phrase):
        self.date_time = date_time
        self.temp = temp
        self.wind = wind
        self.phrase = phrase


class Weather(object):
    def __init__(self):#, name):
        self.__name__ = "Weather"
        # TODO make generic to all Weather locations (not just Seattle)
        self.website_url = "https://weather.com/weather/today/l/USWA0395:1:US"
        self.url_regex = r"^https://weather.com/weather/today/l/([0-9A-Z]+):1:US"

        self.sql_exists = textwrap.dedent("""SELECT * FROM Collector.dbo.Weather WHERE datetime_posted = (?);""")
        self. sql_insert = textwrap.dedent("""
            INSERT INTO Collector.dbo.Weather(datetime_added, datetime_posted, temp, wind, phrase)
                VALUES (?, ?, ?, ?, ?);""")

        self.minutes = 10.0
        self.seconds = 60.0
        self.jitter = 0.17
        self.request_rate_small = float(self.minutes * (1.0 - self.jitter))
        self.request_rate_large = float(self.minutes * (1.0 + self.jitter))
        self.actual_request_rate = self.seconds * random.uniform(self.request_rate_small, self.request_rate_large)
        self.duplicate_factor = 0.25
        self.duplicate_count = 0
        self.insert_count = 0

        self.div_classes = None
        self.duplicate_check = False
        self.insert_failure_check = False

        self.email_messages = list()
        self.weather = list()

        self.date_time_check = list()
        self.date_time_check.append(datetime(2000, 1, 1, 0, 0, 0).time())
        self.date_time_check.append(datetime(2000, 1, 1, 1, 0, 0).time())
        self.date_time_check.append(datetime(2000, 1, 1, 23, 0, 0).time())
        self.date_time_check.append(datetime(2000, 1, 1, 23, 59, 59).time())

    def set_tag(self, bs_obj):
        self.div_classes = bs_obj.find_all(('div', 'p'), re.compile(r'today_nowcard-(temp)|(phrase)|(sidecar)|(timestamp)'))

    def store_scraped_html(self):
        date_time = temp = wind = phrase = "null"

        for i in range(0, len(self.div_classes)):
            line = str(self.div_classes[i])

            # pull relevant lines from HTML
            date_time_match = re.search(r'as of<!-- --> </span><span>(.+?)</span>', line)
            temp_match = re.search(r'temp"><span class="">(.+?)<sup>', line)
            wind_match = re.search(r'</th><td><span class="">(.+?) </span>', line)
            phrase_match = re.search(r'-phrase">(.+?)</div>', line)

            # parse lines looking for regular expression matches
            if date_time_match:
                date_time = date_time_match.group(1)
                weather_time = datetime.strptime(date_time[:-4], '%I:%M %p')
                date_time = datetime.combine(datetime.now(), weather_time.time())

                # ensure the correct date is recorded (midnight bug)
                if self.date_time_check[0] < datetime.now().time() < self.date_time_check[1] \
                        and self.date_time_check[2] < date_time.time() < self.date_time_check[3]:
                    date_time = date_time - timedelta(days=1)
            if temp_match:
                temp = temp_match.group(1)
            if wind_match:
                wind = wind_match.group(1)
                wind = re.sub('[^0-9]', '', wind)
            if phrase_match:
                phrase = phrase_match.group(1)

        # handles wind being 700,000+ MPH bug
        if wind == "null":
            wind = "0"

        self.add(date_time, temp, wind, phrase)

    def add(self, _date_time, _temp, _wind, _phrase):
        self.weather.append(Post(_date_time, _temp, _wind, _phrase))

    def insert(self, start_time, cnxn, cursor):
        for count, entry in enumerate(self.weather):
            insert_success = True
            # print("This is the date type = " + str(type(entry.date_time)))
            # print("This is the date = " + str(entry.date_time))
            if entry.date_time != "null":
                datetime_from_string = datetime.strptime(str(entry.date_time), '%Y-%m-%d %H:%M:%S')
                # print("This is the datetime2String = " + str(datetime_from_string))
                cursor.execute(self.sql_exists, datetime_from_string)
                row = cursor.fetchall()
            else:
                continue

            elapsed = time.time() - start_time
            sleep_length_duplicate = self.duplicate_factor * (self.actual_request_rate - elapsed)
            email_text = "temp = " + str(entry.temp) + "\nposted = " + str(entry.date_time) + \
                         "\ncurrent time = " + str(datetime.now()) + "\nwind = " + entry.wind + "\nphrase = " + entry.phrase

            #
            if len(row) >= 1:
                self.duplicate_count += 1
                self.duplicate_check = True
                print("[duplicate " + str(self.duplicate_count) + "] = " + str(row))
                print("[sleep] = " + str(sleep_length_duplicate))
                time.sleep(sleep_length_duplicate)
                continue
            elif entry.temp == "null":
                self.insert_failure_check = True
                self.duplicate_check = True
                self.email_messages.append(email_text)

                print("\n*****  [entry is null] = " + e.args[1] + "\n" + str(entry.date_time) + "\n" + entry.temp + "\n"
                      + str(entry.wind) + "\n" + entry.phrase)
                time.sleep(sleep_length_duplicate)
                continue
            else:
                try:
                    cursor.execute(self.sql_insert, datetime.now(), entry.date_time, entry.temp, entry.wind, entry.phrase)
                except pyodbc.DatabaseError as e:
                    self.insert_failure_check = True
                    insert_success = False

                    self.email_messages.append(email_text)
                    print("\n*****  [insert failed] = " + e.args[1] + "\n" + str(entry.date_time) + "\n" + entry.temp + "\n"
                          + str(entry.wind) + "\n" + entry.phrase)

                if insert_success is True:
                    self.insert_count += 1
                    print("[insert " + str(self.insert_count) + "] = " + str(datetime.now()) +
                          "\n\t" + entry.temp + "\n\t" + entry.wind + "\n\t" + entry.phrase)

            cnxn.commit()

    def finish(self):
        del self.weather
        del self.email_messages
        self.weather = list()
        self.email_messages = list()
        self.duplicate_check = False
        self.insert_failure_check = False
