# Web-Scraper
This Python web scraper is designed to parse HTML tags, convert them into relevant data, and insert them into a database. The project's original intention was to correlate Reddit's r/Seattle subreddit postings with Seattle's weather conditions. I have only tested this with Python 3.6 and Ubunutu 16.04.

Currently the scraper has only been tested against these two websites:
https://www.reddit.com/r/Seattle/new --- https://weather.com/weather/today/l/USWA0395:1:US

# Tableau Dashboard of Scraped Data
A view of the scraper's data can be accessed in this Tableau dashboard:
https://public.tableau.com/profile/john.fitzgerald7009#!/vizhome/Web-Scraper/rSeattlevs_Weather

# Getting Started
You will need: 
  Pyhton 3.6, 
  a Unix environment (haven't tested in Windows or Mac), 
  BeautifulSoup, 
  PyODBC (and the appropraite drivers for your server), 
  smtplib (email alerts), 
  and the Requests library. 

collector.py will require you to modify some hard coded variables in the main function:
```
database = 'database'
username = 'username'
odbc_credentials = 'DRIVER={ODBC Driver 13 for SQL Server};SERVER=' + db_url + \
                       ';DATABASE=' + database + ';UID=' + username + ';PWD=' + db_pwd
```
Below are the command line arguments for each of the two scripts that should run simultaneously:

# r/Seattle/new collector (runs about every hour)
```
python3 collector.py reddit https://reddit.com/r/Seattle/new <your database> <your email server> <from email> <to email>
```

# Seattle weather collector (runs about ever ten minutes)
```
python3 collector.py weather https://weather.com/weather/today/l/USWA0395:1:US <your database> <your email server> <from email> <to email>
```


This project’s ethical repercussions were thoroughly reviewed. As this is only for educational purposes, it was paramount that I didn’t enact any trespass to chattels. These scripts and actions will bring no harm to the website, no malicious intent is intended or made, and the scripts will not inhibit traffic from reaching the websites. The timing of the requests ensures this.
