# Author: John Fitzgerald
# Title: collector.py
# Date Modified: 12/27/17
# Description: Leave script running to parse a subreddit's new posts, and insert them into a database.
# An email is sent out if the insert fails.
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.mime import multipart, text
import requests
import re
import pytz
import pyodbc
import sys
import getpass
import textwrap
import random
import time
import smtplib
import reddit


# get user's input after validating it
def get_user_input_list(arg, user_input_strings, user_input_options):
    total = 8
    input_values = [""] * total

    if len(arg) >= total - 2:
        for i in range(0, total - 2):
            # print(i)
            input_values[i] = arg[i + 1]
            # print(arg[i + 1])
        # input_values[0] = arg[1]
        # input_values[1] = arg[2]
        # input_values[2] = arg[3]
        # input_values[3] = arg[4]

    return list(get_valid_user_input(input_values, user_input_strings, user_input_options))


# get valid variables from the user
def get_valid_user_input(input_values, user_input_strings, user_input_options):
    for x in range(0, len(input_values)):
        while re.match(user_input_options[x], input_values[x].lower()) is None:
            if 0 < x < 6:
                input_values[x] = input(user_input_strings[x])
            else:
                input_values[x] = getpass.getpass(user_input_strings[x])

    return input_values


# create email message based on collector type
def create_email(_email_from, _email_to, _collector_type):
    message = multipart.MIMEMultipart()
    message['From'] = _email_from
    message['To'] = _email_to
    message['Subject'] = "ALERT: " + _collector_type + " Collector"

    return message


#
def get_email_server(_email_domain, _email_from, _email_pwd):
    server = smtplib.SMTP_SSL(_email_domain)
    server.ehlo()
    server.login(_email_from, _email_pwd)

    return server


#
def get_headers():
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    return headers


#
def send_email(_domain, _pwd, _from, _to, message, message_text):
    message.attach(text.MIMEText(message_text, 'plain'))
    message_text = message.as_string()

    server = get_email_server(_domain, _from, _pwd)
    server.sendmail(_from, _to, message_text)
    server.quit()


def main():
    please_str = "Please enter a valid "
    # TODO determine type and pass regex in afterwards
    user_input_options = [r"weather|reddit", r"^https://reddit.com/r/([0-9a-z]+)",
                          r"(.+)", r"(.+)", r"[^@]+@[^@]+\.[^@]+", r"[^@]+@[^@]+\.[^@]+", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "collector type: ", please_str + "url (scraping): ", please_str + "url (database): ",
                          please_str + "email (domain): ", please_str + "email (from): ", please_str + "email (to): ",
                          please_str + "email (pwd): ", please_str + "database (pwd): "]

    collector_type, website_url, db_url, email_domain, email_from, email_to, email_pwd, db_pwd, *rest = \
        list(get_user_input_list(sys.argv, user_input_strings, user_input_options))

    if collector_type == "reddit":
        collector_obj = reddit.Reddit(website_url)
    # else:
    #     collector_obj = weather.Weather(website_url)

    server = get_email_server(email_domain, email_from, email_pwd)
    server.quit()
    message = create_email(email_from, email_to, collector_type)
    session = requests.Session()
    headers = get_headers()

    database = 'Collector'
    username = 'Wobey'
    total_run_start_time = time.time()

    while True:
        print("\n\t\tTOTAL RUNTIME = " + str(time.time() - total_run_start_time) + "\n")

        start_time = time.time()

        # get HTML request
        req = session.get(website_url, headers=headers)
        bs_obj = BeautifulSoup(req.text, "lxml")

        collector_obj.set_tag(bs_obj)
        collector_obj.loop_for_posts()

        # initialize connection to database using installed ODBC SQL Server driver
        # TODO try except for connection errors (ask to re-enter password)
        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + db_pwd)
        cursor = cnxn.cursor()

        # insert posts into database
        collector_obj.insert(start_time, cnxn, cursor)

        # send any available emails
        if len(collector_obj.email_messages) > 0:
            for message_text in collector_obj.email_messages:
                send_email(email_domain, email_from, email_to, email_pwd, message, message_text)

        cnxn.close()

        elapsed = time.time() - start_time
        if elapsed < collector_obj.actual_request_rate and collector_obj.duplicate_check is False:
            print("[sleep] = " + str(collector_obj.actual_request_rate - elapsed))
            time.sleep(collector_obj.actual_request_rate - elapsed)
            collector_obj.actual_request_rate = collector_obj.seconds * \
                                                random.uniform(collector_obj.request_rate_small, collector_obj.request_rate_large)


if __name__ == "__main__":
    main()
