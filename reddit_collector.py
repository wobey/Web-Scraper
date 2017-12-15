# Author: John Fitzgerald
# Title: reddit_collector.py
# Date Modified: 12/14/17
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


def send_email(domain, pwd, _from, _to, message, title, posted):
    message.attach(text.MIMEText("title = " + title + "\nposted = " + str(posted), 'plain'))
    message_text = message.as_string()

    server = smtplib.SMTP_SSL(domain)
    server.ehlo()
    server.login(_from, pwd)

    server.sendmail(_from, _to, message_text)
    server.quit()


def main():
    comment_url = "r/Seattle/comments/"
    please_str = "Please enter a valid "
    user_input_options = [r"^https://reddit.com/r/([0-9A-Z]+)", r"(.+)", r"(.+)", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "subreddit url: ", please_str + "db url: ", please_str + "email domain: ",
                          please_str + "email pwd: ", please_str + "db pwd: "]

    # *rest catches the rest of the list
    subreddit_url, db_url, email_domain, email_pwd, db_pwd, *rest = list(get_user_input_list(sys.argv, user_input_strings, user_input_options))

    # test email login
    email_address_from = "yebow@comcast.net"
    email_address_to = "wobey@uw.edu"

    server = smtplib.SMTP_SSL(email_domain)
    server.ehlo()
    server.login(email_address_from, email_pwd)
    server.quit()

    # create email (sent if error is detected)
    message = multipart.MIMEMultipart()
    message['From'] = email_address_from
    message['To'] = email_address_to
    message['Subject'] = "ALERT:  Reddit Collector"

    session = requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    minutes = 60.0
    seconds = 60.0
    jitter = 0.17
    request_rate_small = float(minutes * (1.0 - jitter))
    request_rate_large = float(minutes * (1.0 + jitter))
    actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)
    duplicate_factor = 0.5
    duplicate_count = 0
    insert_count = 0

    total_run_start_time = time.time()

    while True:
        print("\n\t\tTOTAL RUNTIME = " + str(time.time() - total_run_start_time) + "\n")

        start_time = time.time()
        posts = post.Posts(subreddit_url)
        duplicate_check = False

        # get HTML request
        req = session.get(subreddit_url, headers=headers)
        bs_obj = BeautifulSoup(req.text, "lxml")
        div_classes = bs_obj.find_all('div', attrs={'class': re.compile(r'thing$')})

        title = date_time = user = url = "null"

        for i in range(0, len(div_classes)):
            line = str(div_classes[i])

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
                if comment_url in url:
                    url = "https://reddit.com" + url

            posts.add(date_time, title, user, url)
            title = date_time = user = url = "null"

        # initialize connection to database using installed ODBC SQL Server driver
        database = 'Collector'
        username = 'Wobey'
        password = db_pwd
        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = cnxn.cursor()

        # insert posts into database
        for count, (key, value) in enumerate(posts.posts.items()):
            sql_exists = textwrap.dedent("""SELECT * FROM Collector.guest.Posts WHERE datetime_posted = (?) and username = (?);""")
            cursor.execute(sql_exists, value.date_time, value.user)
            row = cursor.fetchall()

            # because r/Seattle/new orders postings by time, the first duplicate should trigger a break
            if len(row) >= 1:
                duplicate_count += 1
                print("[duplicate " + str(duplicate_count) + "] = " + str(row))

                # sleep for a quarter of the time to attempt a faster request
                elapsed = time.time() - start_time
                sleep_length = duplicate_factor * (actual_request_rate - elapsed)

                print("[sleep] = " + str(sleep_length))
                time.sleep(sleep_length)
                duplicate_check = True
                break
            else:
                sql_insert = textwrap.dedent("""
                INSERT INTO Collector.guest.Posts(datetime_added, datetime_posted, username, url_path, title)
                    VALUES (?, ?, ?, ?, ?);""")

                # trigger email if the insert was unsuccessful
                try:
                    cursor.execute(sql_insert, datetime.now(), value.date_time, value.user, value.url, value.title)
                except pyodbc.DatabaseError as e:
                    send_email(email_domain, email_pwd, email_address_from, email_address_to, message, value.title, value.date_time)
                    raise e("Insert failed = " + str(value.title))

                insert_count += 1
                print("[insert " + str(insert_count) + "] = " + str(datetime.now()))
                print("\t" + value.title)

            # trigger email if the insert was unsuccessful
            try:
                cnxn.commit()
            except pyodbc.DatabaseError as e:
                send_email(email_domain, email_pwd, email_address_from, email_address_to, message, value.title, value.date_time)
                raise e('Insert failed.')

        elapsed = time.time() - start_time
        if elapsed < actual_request_rate and duplicate_check is False:
            print("[sleep] = " + str(actual_request_rate - elapsed))
            time.sleep(actual_request_rate - elapsed)
            actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)

        del posts


if __name__ == "__main__":
    main()
