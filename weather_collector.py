import requests
from bs4 import BeautifulSoup
import re
import weather
from datetime import datetime, timedelta
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
    user_input_options = [r"^https://weather.com/weather/today/l/([0-9A-Z]+):1:US", r"(.+)", r"(.+)", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "weather url: ", please_str + "db url: ", please_str + "email domain: ",
                          please_str + "email pwd: ", please_str + "db pwd: "]

    # *rest catches the rest of the list
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
    message.attach(text.MIMEText("empty", 'plain'))
    message_text = message.as_string()

    session = requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    # url = "https://reddit.com/r/Seattle/new"
    # url = "https://weather.com/weather/today/l/USMN0503:1:US"     # Everett
    # weather_url = "https://weather.com/weather/today/l/USWA0395:1:US"       # Seattle

    minutes = 10.0
    seconds = 60.0
    jitter = 0.17
    request_rate_small = float(minutes * (1.0 - jitter))
    request_rate_large = float(minutes * (1.0 + jitter))
    actual_rph = seconds * random.uniform(request_rate_small, request_rate_large)
    duplicate_factor = 0.5

    # print("Request rate small = " + str(request_rate_small))
    # print("Request rate large = " + str(request_rate_large))
    # print("Actual rph = " + str(actual_rph))

    duplicate_count = 0
    insert_count = 0

    total_run_start_time = time.time()

    while True:
        print("\n\t\tTOTAL RUNTIME = " + str(time.time() - total_run_start_time))

        start_time = time.time()

        req = session.get(weather_url, headers=headers)

        bs_obj = BeautifulSoup(req.text, "lxml")
        # print(bs_obj.prettify())

        # create a hash of objects (Post classes) to hold each post
        Weather = weather.Weather(weather_url)

        div_classes = bs_obj.find_all(('div', 'p'), re.compile(r'today_nowcard-(temp)|(phrase)|(sidecar)|(timestamp)'))

        date_time_check = []
        date_time_check.append(datetime(2000, 1, 1, 0, 0, 0).time())
        date_time_check.append(datetime(2000, 1, 1, 1, 0, 0).time())
        date_time_check.append(datetime(2000, 1, 1, 23, 0, 0).time())
        date_time_check.append(datetime(2000, 1, 1, 23, 59, 59).time())

        # for div in div_classes:
        #     print(div)
        # print()

        date_time = temp = wind = phrase = "null"

        # get everything in from first '>' to '</a>
        for i in range(0, len(div_classes)):
            line = str(div_classes[i])

            date_time_match = re.search(r'as of<!-- --> </span><span>(.+?)</span>', line)
            temp_match = re.search(r'temp"><span class="">(.+?)<sup>', line)
            wind_match = re.search(r'</th><td><span class="">(.+?) </span>', line)
            phrase_match = re.search(r'-phrase">(.+?)</div>', line)

            if date_time_match:
                date_time = date_time_match.group(1)
                weather_time = datetime.strptime(date_time[:-4], '%I:%M %p')
                date_time = datetime.combine(datetime.now(), weather_time.time())

                # ensure the correct date is recorded (midnight bug)
                if date_time_check[0] < datetime.now().time() < date_time_check[1] \
                        and date_time_check[2] < date_time.time() < date_time_check[3]:
                    date_time = date_time - timedelta(days=1)

                tz = pytz.timezone('America/Los_Angeles')
                # print(datetime.now(tz=tz).replace(tzinfo=None))
            if temp_match:
                temp = temp_match.group(1)
            if wind_match:
                wind = wind_match.group(1)
                wind = re.sub('[^0-9]', '', wind)
            if phrase_match:
                phrase = phrase_match.group(1)

        if wind == "null":
            wind = "0"

        # Weather.add(date_time, temp, wind, phrase)
        # date_time = temp = wind = phrase = "null"

        server = db_url
        database = 'Collector'
        username = 'Wobey'
        password = db_pwd
        cnxn = pyodbc.connect(
            'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + server + ';DATABASE=' + database + ';UID=' + username + ';PWD=' + password)
        cursor = cnxn.cursor()

        # for count, (key, value) in enumerate(Weather.weather.items()):
        sql_exists = textwrap.dedent("""SELECT * FROM Collector.guest.Weather WHERE datetime_posted = (?);""")
        cursor.execute(sql_exists, date_time)
        # cursor.execute(sql_exists, value.date_time)
        print("\n[scraped HTML] = " + str(date_time))
        # print("\n[scraped HTML] = " + str(value.date_time))

        row = cursor.fetchall()

        if len(row) >= 1:
            duplicate_count += 1
            print("[duplicate " + str(duplicate_count) + "] = " + str(row))
            # sleep for a quarter of the time to attempt a faster request
            elapsed = time.time() - start_time
            sleep_length = duplicate_factor * (actual_rph - elapsed)
            print("[sleep] = " + str(sleep_length))
            time.sleep(sleep_length)

            continue
        else:
            sql_insert = textwrap.dedent("""
            INSERT INTO Collector.guest.Weather(datetime_added, datetime_posted, temp, wind, phrase)
                VALUES (?, ?, ?, ?, ?);""")

            cursor.execute(sql_insert, datetime.now(), date_time, temp, wind, phrase)
            # cursor.execute(sql_insert, datetime.now(), value.date_time, value.temp, value.wind, value.phrase)

            insert_count += 1
            print("[insert " + str(insert_count) + "] = " + str(datetime.now()))
            print("\t" + str(date_time))
            print("\t" + temp)
            print("\t" + wind)
            print("\t" + phrase)
            # print("\t" + value.phrase)print("System time = " + str(datetime.now()))
            # print("\t" + str(value.date_time))
            # print("\t" + value.temp)
            # print("\t" + value.wind)
            # print("\t" + value.phrase)

        date_time = temp = wind = phrase = "null"

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
        if elapsed < actual_rph:
            print("[sleep] = " + str(actual_rph - elapsed))
            time.sleep(actual_rph - elapsed)
            actual_rph = seconds * random.uniform(request_rate_small, request_rate_large)


if __name__ == "__main__":
    main()
