# Web-Scraper
[This Python web scraper is designed to parse HTML tags, convert them into relevant data, and insert them into a database. The project's original intention was to correlate Reddit's r/Seattle subreddit postings with Seattle's weather conditions. I have only tested this with Python 3.6 and Ubunutu 16.04.

Currently the scraper has only been tested against these two websites:
* https://www.reddit.com/r/Seattle/new
* https://weather.com/weather/today/l/USWA0395:1:US

## Tableau Dashboard of Scraped Data
I created a Tableau Dashboard (an interactive visual) of the data I scraped using these scripts. Single days are selected through a scroll bar at the top of the dashboard. Each day categorizes Reddit posts by their corresponding weather phrase, and orders the posts by temperature. The user can highlight the post's title to see further inforamtion on the post and correlated weather. The user may also click the title to be taken to the post's url.

https://public.tableau.com/profile/john.fitzgerald7009#!/vizhome/Web-Scraper/rSeattlevs_Weather

## Getting Started
### Requirements
You will need: 
1) Pyhton 3.6, 
2) Linux environment (haven't tested in Windows or Mac), 
3) BeautifulSoup, 
4) PyODBC (and the appropraite drivers for your server), 
5) smtplib (for automated email alerts), 
6) the Requests library,
7) and a database + appropriate tables (I will not provide a guide for that).

collector.py will require you to modify these hard coded variables in the main function after you setup your database and ODBC driver:
```python
database = 'database'
username = 'username'
odbc_credentials = 'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + \
                       ';DATABASE=' + database + ';UID=' + username + ';PWD=' + db_pwd
```

### Loop Logic
After the environments have been set up, and the scripts are executed (as shown below), the basic loop logic is as follows:
1) display overall program execution time (hours),
2) http request to website, 
3) parse out relevant HTML tags from request, 
4) parse with regular expression to determine data, 
5) establish ODBC connection to database,
6) insert data into table if not a duplicate,
7) display: scraped data, duplicate or insert, and the amount of sleep until next loop (seconds).

Below are the command line arguments for each of the two scripts:

### r/Seattle/new collector (runs about every hour)
```
python3 collector.py reddit https://reddit.com/r/Seattle/new <your database> <your email server> <from email> <to email>
```

### Seattle weather collector (runs about every ten minutes)
```
python3 collector.py weather https://weather.com/weather/today/l/USWA0395:1:US <your database> <your email server> <from email> <to email>
```

## Education Purposes
This project’s ethical repercussions were thoroughly reviewed. As this is only for educational purposes, it was paramount that I didn’t enact any trespass to chattels. These scripts and actions will bring no harm to the website, no malicious intent is intended or made, and the scripts will not inhibit traffic from reaching the websites. The timing of the requests ensures this.
