# Author: John Fitzgerald
# Title: collector.py
# Date Modified: 12/27/17
# Description: Leave script running to parse a subreddit's new posts, and insert them into a database.
# An email is sent out if the insert fails.
from bs4 import BeautifulSoup
from email.mime import multipart, text
import requests
import re
import pyodbc
import sys
import getpass
import random
import time
import smtplib
import reddit
import weather


# get user's input after validating it
def get_user_input_list(arg, user_input_strings, user_input_options):
    total = 8
    input_values = [""] * total

    # store reg expression based on user input type
    collector_obj = get_collector_obj(user_input_options[0], arg[1])
    # print("***CLASS OBJ NAME = " + collector_obj.__name__)
    # user_input_options[1] = collector_obj.url_regex

    if len(arg) >= total - 2:
        for i in range(0, total - 2):
            input_values[i] = arg[i + 1]

    user_input_options[1] = collector_obj.url_regex
    input_values[1] = collector_obj
    # user_input_options[1] = r"(.+)"
    # print(user_input_options[1])

    return list(get_valid_user_input(input_values, user_input_strings, user_input_options, total))


#
def get_collector_obj(collector_options, collector_type):
    while re.match(collector_options, collector_type.lower()) is None:
        collector_type = input(collector_options)

    # return reduce(getattr, collector_type.split("."), sys.module[__name__])
    # return eval(collector_type)
    # return globals()[collector_type]
    return getattr(globals()[collector_type], collector_type.title())()


# get valid variables from the user
def get_valid_user_input(input_values, user_input_strings, user_input_options, total_input):
    for x in range(0, len(input_values)):
        if x == 1:  # collector object handled outside
            continue
        while re.match(user_input_options[x], input_values[x].lower()) is None:
            if 0 < x < total_input - 2:
                input_values[x] = input(user_input_strings[x])
            else:
                input_values[x] = getpass.getpass(user_input_strings[x])

    return input_values


# create email message based on collector type
def get_email_message(_email_from, _email_to, _collector_type):
    message = multipart.MIMEMultipart()
    message['From'] = _email_from
    message['To'] = _email_to
    message['Subject'] = "ALERT: " + str(_collector_type).upper() + " collector"

    return message


# get the email server from smtplib
def get_email_server(_email_domain, _email_from, _email_pwd):
    server = smtplib.SMTP_SSL(_email_domain)
    server.ehlo()
    server.login(_email_from, _email_pwd)

    return server


# gets a header to alter credentials
def get_headers():
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    return headers


# sends an email with a collector dependent message
def send_email(_domain, _pwd, _from, _to, message, message_text):
    message.attach(text.MIMEText(message_text, 'plain'))
    message_text = message.as_string()

    server = get_email_server(_domain, _from, _pwd)
    server.sendmail(_from, _to, message_text)
    server.quit()


# sleep if there weren't duplicates during insertion
def sleep_on_no_duplicate(elapsed, collector_obj):
    if elapsed < collector_obj.actual_request_rate and collector_obj.duplicate_check is False:
        print("[sleep] = " + str(collector_obj.actual_request_rate - elapsed))
        time.sleep(collector_obj.actual_request_rate - elapsed)
        collector_obj.actual_request_rate = collector_obj.seconds * \
                                            random.uniform(collector_obj.request_rate_small,
                                                           collector_obj.request_rate_large)


def main():
    please_str = "Please enter a valid "
    # TODO re-organize without reg ex check in user_input_options
    user_input_options = [r"weather|reddit", "",
                          r"(.+)", r"(.+)", r"[^@]+@[^@]+\.[^@]+", r"[^@]+@[^@]+\.[^@]+", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "collector type: ", please_str + "url (scraping): ", please_str + "url (database): ",
                          please_str + "email (domain): ", please_str + "email (from): ", please_str + "email (to): ",
                          please_str + "email (password): ", please_str + "database (password): "]

    # TODO store website url

    collector_type, collector_obj, db_url, email_domain, email_from, email_to, email_pwd, db_pwd, *rest = \
        list(get_user_input_list(sys.argv, user_input_strings, user_input_options))

    # print(collector_obj.__name__, db_url, email_domain, email_from, email_to, email_pwd, db_pwd)

    server = get_email_server(email_domain, email_from, email_pwd)  # test server credentials
    server.quit()
    message = get_email_message(email_from, email_to, collector_obj.__name__)
    session = requests.Session()
    headers = get_headers()

    database = 'Collector'
    username = 'Wobey'
    odbc_credentials = 'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url +\
                       ';DATABASE=' + database + ';UID=' + username + ';PWD=' + db_pwd
    total_run_start_time = time.time()

    # TODO break if unable to connect after 3 times
    while True:
        print("\n\t\tTOTAL RUNTIME (hours) = " + str((time.time() - total_run_start_time) / 3600) + "\n")
        start_time = time.time()

        # get HTML request
        req = session.get(collector_obj.website_url, headers=headers)
        bs_obj = BeautifulSoup(req.text, "lxml")

        collector_obj.set_tag(bs_obj)
        collector_obj.store_scraped_html()

        cnxn = pyodbc.connect(odbc_credentials)
        cursor = cnxn.cursor()

        collector_obj.insert(start_time, cnxn, cursor)

        # send insert-error emails
        if collector_obj.insert_failure_check is True:
            for message_text in collector_obj.email_messages:
                print(message_text)
                send_email(email_domain, email_from, email_to, email_pwd, message, message_text)

        cnxn.close()

        elapsed = time.time() - start_time
        sleep_on_no_duplicate(elapsed, collector_obj)
        collector_obj.finish()


if __name__ == "__main__":
    main()
