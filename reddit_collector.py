import requests
from bs4 import BeautifulSoup
import re
import post
from datetime import datetime, timedelta, timezone
import pytz
import pyodbc
import sys
import getpass
import textwrap
import random
import time
import smtplib
from email.mime import multipart, text


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


def main():
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

    message = multipart.MIMEMultipart()
    message['From'] = email_address_from
    message['To'] = email_address_to
    message['Subject'] = "ALERT:  Reddit Collector"
    message.attach(text.MIMEText("empty", 'plain'))
    message_text = message.as_string()

    comment_url = "r/Seattle/comments/"

    session = requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    # subreddit_url = "https://reddit.com/r/Seattle/new"
    # url = "https://weather.com/weather/hourbyhour/l/98203:4:US"

    minutes = 60.0
    seconds = 60.0
    jitter = 0.17
    request_rate_small = float(minutes * (1.0 - jitter))
    request_rate_large = float(minutes * (1.0 + jitter))
    actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)
    duplicate_factor = 0.4

    # print("Request rate small = " + str(request_rate_small))
    # print("Request rate large = " + str(request_rate_large))
    # print("Actual request rate = " + str(actual_request_rate))

    duplicate_count = 0
    insert_count = 0

    total_run_start_time = time.time()

    while True:
        print("\n\t\tTOTAL RUNTIME = " + str(time.time() - total_run_start_time) + "\n")

        start_time = time.time()

        req = session.get(subreddit_url, headers=headers)

        bs_obj = BeautifulSoup(req.text, "lxml")
        # print(bs_obj.prettify())

        Posts = post.Posts(subreddit_url)

        div_classes = bs_obj.find_all('div', attrs={'class': re.compile(r'thing$')})

        # for div in div_classes:
        #     print(div)
        # print()

        title = date_time = user = url = "null"

        for i in range(0, len(div_classes)):
            line = str(div_classes[i])

            title_match = re.search(r'tabindex="1">(.+?)</a>', line)
            # title_match = re.search(r'>(.+?)</a>', str(titles[i]))
            time_match = re.search(r'data-timestamp="(.+?)"', line)
            # time_match = re.search(r'"datetime="(.+?)"', str(times[i]))
            user_match = re.search(r'data-author="(.+?)"', line)
            url_match = re.search(r'href="(.+?)" rel="', line)

            if title_match:
                title = title_match.group(1)
            if time_match:
                date_time = time_match.group(1)
                date_time = datetime.utcfromtimestamp(int(date_time[:-3]))  # convert to UTC date time
                tz = pytz.timezone('America/Los_Angeles')
                date_time = pytz.utc.localize(date_time, is_dst=None).astimezone(tz).replace(tzinfo=None)  # convert to Seattle time
            if user_match:
                user = user_match.group(1)
            if url_match:
                url = url_match.group(1)
                if comment_url in url:
                    url = "https://reddit.com" + url

            Posts.add(date_time, title, user, url)
            title = date_time = user = url = "null"

        # for count, (key, value) in enumerate(Posts.posts.items()):
        #     print(str(count + 1) + ") " + key)
        #     print("\t" + str(value.date_time))
        #     print("\t" + value.user)
        #     print("\t" + value.url)
        #     print("\t" + value.title)

        server = db_url
        database = 'Collector'
        username = 'Wobey'
        password = db_pwd
        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = cnxn.cursor()

        duplicate = False

        for count, (key, value) in enumerate(Posts.posts.items()):
            # determine if duplicate exists (based on datetime added and username)

            sql_exists = textwrap.dedent("""SELECT * FROM Collector.guest.Posts WHERE datetime_posted = (?) and username = (?);""")
            cursor.execute(sql_exists, value.date_time, value.user)
            # print("\n[scraped HTML] = " + str(value.date_time))
            row = cursor.fetchall()

            # because r/Seattle/new orders postings by time, the first duplicate should trigger a break
            if len(row) >= 1:
                duplicate_count += 1
                print("[duplicate " + str(duplicate_count) + "] = " + str(row))

                break
            else:
                sql_insert = textwrap.dedent("""
                INSERT INTO Collector.guest.Posts(datetime_added, datetime_posted, username, url_path, title)
                    VALUES (?, ?, ?, ?, ?);""")

                cursor.execute(sql_insert, datetime.now(), value.date_time, value.user, value.url, value.title)
                # cursor.execute(sql_insert, datetime.now(), value.date_time, value.temp, value.wind, value.phrase)

                insert_count += 1
                print("[insert " + str(insert_count) + "] = " + str(datetime.now()))
                print("\t" + value.title)
                # print("\t" + str(value.date_time))
                # print("\t" + value.user)
                # print("\t" + value.url)
                # print("\t" + value.title)

            try:
                cnxn.commit()
            except pyodbc.DatabaseError as e:
                print("*** DatabaseError: " + str(e))
                server = smtplib.SMTP_SSL(email_domain)
                server.ehlo()
                server.login(email_address_from, email_pwd)

                server.sendmail(email_address_from, email_address_to, message_text)
                server.quit()
                pass

        elapsed = time.time() - start_time
        if elapsed < actual_request_rate:
            print("[sleep] = " + str(actual_request_rate - elapsed))
            time.sleep(actual_request_rate - elapsed)
            actual_request_rate = seconds * random.uniform(request_rate_small, request_rate_large)

        # TODO free up Posts depending on memory useage
        del Posts


if __name__ == "__main__":
    main()
