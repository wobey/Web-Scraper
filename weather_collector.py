import requests
from urllib.request import urlopen  # to fetch the web page
from bs4 import BeautifulSoup       # to interpret the web page
from urllib.error import HTTPError
from urllib.error import URLError
import re
import weather
from datetime import datetime, timedelta
import pytz
import pyodbc
import random
import smtplib
import sys
import getpass
import textwrap


# get user's input after validating it
def get_user_input_list(arg, user_input_strings, user_input_options):
    input_values = [""] * 4

    if len(arg) >= 3:
        input_values[0] = arg[1]
        input_values[1] = arg[2]

    return list(get_valid_user_input(input_values, user_input_strings, user_input_options))


# get valid variables from the user
def get_valid_user_input(input_values, user_input_strings, user_input_options):
    for x in range(0, len(input_values)):
        while re.match(user_input_options[x], input_values[x]) is None:
            if x == 0 or x == 1:
                input_values[x] = input(user_input_strings[x])
            else:
                input_values[x] = getpass.getpass(user_input_strings[x])

    return input_values


def main():
    please_str = "Please enter a valid "
    user_input_options = [r"^https://weather.com/weather/today/l/([0-9A-Z]+):1:US", r"(.+)", r"(.+)", r"(.+)"]
    user_input_strings = [please_str + "weather url: ", please_str + "db url: ", please_str + "email pwd: ", please_str + "db pwd: "]

    # *rest catches the rest of the list
    weather_url, db_url, email_pwd, db_pwd, *rest = list(get_user_input_list(sys.argv, user_input_strings, user_input_options))

    #TODO erase repo and replace with non-password

    session = requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                            "AppleWebKit/537.36 (KHTML, like Gecko)"
                            "Chrome/61.0.3163.100 Safari/537.36",
               "Accept":"text/html,application/xhtml+xml,application/xml"
                        ";q=0.9,image/webp,image/apng,*/*;q=0.8"}

    # url = "https://reddit.com/r/Seattle/new"
    # url = "https://weather.com/weather/today/l/USMN0503:1:US"     # Everett
    # weather_url = "https://weather.com/weather/today/l/USWA0395:1:US"       # Seattle

    # TODO add jitterered while loop

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
            if date_time_check[0] < datetime.now().time() < date_time_check[1]\
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

    Weather.add(date_time, temp, wind, phrase)
    date_time = temp = wind = phrase = ""

    server = db_url
    database = 'Collector'
    username = 'Wobey'
    password = db_pwd
    cnxn = pyodbc.connect('DRIVER={ODBC Driver 13 for SQL Server};SERVER='+server+';DATABASE='+database+';UID='+username+';PWD='+ password)
    cursor = cnxn.cursor()

    for count, (key, value) in enumerate(Weather.weather.items()):
        # if not exists (select * from Collector.guest.Weather where
        # """)

        sql_exists = textwrap.dedent("""select * from Collector.guest.Weather where datetime_posted = (?);""")
        cursor.execute(sql_exists, value.date_time)
        print("HTML = " + str(value.date_time))

        # for count_fetch, row in enumerate(cursor.fetchone()):
        row = cursor.fetchall()
        if len(row) >= 1:
            print("SQL = " + str(row))
        else:
            sql_insert = textwrap.dedent("""
            insert into Collector.guest.Weather(datetime_added, datetime_posted, temp, wind, phrase)
                values (?, ?, ?, ?, ?);""")

            cursor.execute(sql_insert, datetime.now(), value.date_time, value.temp, value.wind, value.phrase)

        print(str(count + 1) + ") " + str(datetime.now()))
        print("\t" + str(value.date_time))
        print("\t" + value.temp)
        print("\t" + value.wind)
        print("\t" + value.phrase)

        try:
            cnxn.commit()
        except pyodbc.DatabaseError as e:
            print("*** DatabaseError: " + str(e))
            # TODO send email

            pass


if __name__ == "__main__":
    main()
