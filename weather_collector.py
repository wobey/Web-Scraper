# Author: John Fitzgerald
# Title: weather_collector.py
# Date Modified: 12/14/17
# Description: Leave script running to parse a the current weather, and insert it into a database.
# An email is sent out if the insert fails.
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.mime import multipart, text
import requests
import re
import pyodbc
import sys
import getpass
import textwrap
import random
import time
import smtplib


# get user's input after validating it
def get_user_input_list(arg, user_input_strings, user_input_options):
    input_values = [""] * 5

    if len(arg) >= 4:
        input_values[0] = arg[1]
        input_values[1] = arg[2]
        input_values[2] = arg[3]

    return list(get_valid_user_input(input_values, user_input_strings, user_input_options))


# get valid variables from the user
def get_valid_user_input(input_values, user_input_strings, user_input_options):
    for x in range(0, len(input_values)):
        while re.match(user_input_options[x], input_values[x]) is None:
            if 0 < x < 3:
                input_values[x] = input(user_input_strings[x])
            else:
                input_values[x] = getpass.getpass(user_input_strings[x])

    return input_values


def send_email(domain, pwd, _from, _to, message, temp, posted):
    message.attach(text.MIMEText("temp = " + str(temp) + "\nposted = " + str(posted), 'plain'))
    message_text = message.as_string()

    server = smtplib.SMTP_SSL(domain)
    server.ehlo()
    server.login(_from, pwd)

    server.sendmail(_from, _to, message_text)
    server.quit()


def main():
    please_str = "Please enter a valid "
    user_input_options = [r"^https://weather.com/weather/today/l/([0-9A-Z]+):1:US", r"(.+)", r"(.+)", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "weather url: ", please_str + "db url: ", please_str + "email domain: ",
                          please_str + "email pwd: ", please_str + "db pwd: "]

    weather_url, db_url, email_domain, email_pwd, db_pwd, *rest = list(get_user_input_list(sys.argv, user_input_strings, user_input_options))

    # test email login
    email_address_from = "yebow@comcast.net"
    email_address_to = "wobey@uw.edu"

    server = smtplib.SMTP_SSL(email_domain)
    server.ehlo()
    server.login(email_address_from, email_pwd)
    server.quit()

    message = multipart.MIMEMultipart()
    message['From'] = email_address_from
    message['To'] = email_address_to
    message['Subject'] = "ALERT:  Weather Collector"

    session = requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    database = 'Collector'
    username = 'Wobey'
    password = db_pwd

    minutes = 10.0
    seconds = 60.0
    jitter = 0.17
    request_rate_small = float(minutes * (1.0 - jitter))
    request_rate_large = float(minutes * (1.0 + jitter))
    actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)
    duplicate_factor = 0.25
    duplicate_count = 0
    insert_count = 0

    date_time_check = list()
    date_time_check.append(datetime(2000, 1, 1, 0, 0, 0).time())
    date_time_check.append(datetime(2000, 1, 1, 1, 0, 0).time())
    date_time_check.append(datetime(2000, 1, 1, 23, 0, 0).time())
    date_time_check.append(datetime(2000, 1, 1, 23, 59, 59).time())

    total_run_start_time = time.time()



    # # insert manually
    # # create weather from 9am - 12pm for Dec 25th (18 entries)
    # date_time_array_9_12pm = list()
    # date_time_array_9_12pm.append(datetime(2018, 1, 1, 16, 23, 0))
    # count = 1
    # while count <= 11:
    #     date_time_array_9_12pm.append(date_time_array_9_12pm[count - 1] + timedelta(minutes=10))
    #     count += 1
    #
    # print(str(len(date_time_array_9_12pm)))
    # print(date_time_array_9_12pm)
    #
    # cnxn = pyodbc.connect(
    #     'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
    # cursor = cnxn.cursor()
    #
    # wind = 6
    # temps = (["41"] * 3) + (["40"] * 3) + (["39"] * 3) + (["38"] * 1) + (["37"] * 2)
    # phrases = (["Fair"] * 4) + (["Clear"] * 8)
    #
    # sql_insert = textwrap.dedent("""
    #                             INSERT INTO Collector.guest.Weather(datetime_added, datetime_posted, temp, wind, phrase)
    #                                 VALUES (?, ?, ?, ?, ?);""")
    #
    # for count, entries in enumerate(date_time_array_9_12pm):
    #     cursor.execute(sql_insert, datetime.now(), date_time_array_9_12pm[count], temps[count], wind, phrases[count])
    #
    # cnxn.commit()
    # cnxn.close()  # set pooling to close to ACTUALLY close connection? [pyodbc.pooling = False]




    while True:
        print("\n\t\tTOTAL RUNTIME (hours) = " + str((time.time() - total_run_start_time) / 3600) + "\n")

        start_time = time.time()

        # get HTML request
        req = session.get(weather_url, headers=headers)
        bs_obj = BeautifulSoup(req.text, "lxml")
        div_classes = bs_obj.find_all(('div', 'p'), re.compile(r'today_nowcard-(temp)|(phrase)|(sidecar)|(timestamp)'))

        insert_success = True
        date_time = temp = wind = phrase = "null"

        for i in range(0, len(div_classes)):
            line = str(div_classes[i])

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
                if date_time_check[0] < datetime.now().time() < date_time_check[1] \
                        and date_time_check[2] < date_time.time() < date_time_check[3]:
                    date_time = date_time - timedelta(days=1)
            if temp_match:
                temp = temp_match.group(1)
            if wind_match:
                wind = wind_match.group(1)
                wind = re.sub('[^0-9]', '', wind)
            if phrase_match:
                phrase = phrase_match.group(1)

        if temp == "null" or date_time == "null":
            send_email(email_domain, email_pwd, email_address_from, email_address_to, message, temp,
                       datetime.now())
            time.sleep(actual_request_rate)
            continue

        # handles wind being 700,000+ MPH bug
        if wind == "null":
            wind = "0"

        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = cnxn.cursor()

        sql_exists = textwrap.dedent("""SELECT * FROM Collector.guest.Weather WHERE datetime_posted = (?);""")
        print("\n[scraped HTML] = " + str(date_time))

        try:
            cursor.execute(sql_exists, date_time)
        except pyodbc.DatabaseError as e:
            send_email(email_domain, email_pwd, email_address_from, email_address_to, message, temp,
                       date_time)
            print("\n*****  [check failed] = " + e.args[1] + "\n" + str(date_time))

        row = cursor.fetchall()

        if len(row) >= 1:
            duplicate_count += 1
            print("[duplicate " + str(duplicate_count) + "] = " + str(row))

            # sleep for a quarter of the time to attempt a faster request
            elapsed = time.time() - start_time
            sleep_length = duplicate_factor * (actual_request_rate - elapsed)
            print("[sleep] = " + str(sleep_length))
            time.sleep(sleep_length)
            continue
        else:
            sql_insert = textwrap.dedent("""
            INSERT INTO Collector.guest.Weather(datetime_added, datetime_posted, temp, wind, phrase)
                VALUES (?, ?, ?, ?, ?);""")

            try:
                cursor.execute(sql_insert, datetime.now(), date_time, temp, wind, phrase)
            except pyodbc.DatabaseError as e:
                insert_success = False
                send_email(email_domain, email_pwd, email_address_from, email_address_to, message, temp,
                           date_time)
                print("\n*****  [insert failed] = " + e.args[1] + "\n" + str(date_time) + "\n" + temp + "\n"
                      + str(wind) + "\n" + phrase)

            if insert_success is True:
                insert_count += 1
                print("[insert " + str(insert_count) + "] = " + str(datetime.now()))
                print("\t" + str(date_time))
                print("\t" + temp)
                print("\t" + wind)
                print("\t" + phrase)

        cnxn.commit()
        cnxn.close()    # set pooling to close to ACTUALLY close connection? [pyodbc.pooling = False]

        elapsed = time.time() - start_time
        if elapsed < actual_request_rate:
            print("[sleep] = " + str(actual_request_rate - elapsed))
            time.sleep(actual_request_rate - elapsed)
            actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)


if __name__ == "__main__":
    main()
