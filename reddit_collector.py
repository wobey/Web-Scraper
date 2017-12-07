import requests
from urllib.request import urlopen  # to fetch the web page
from bs4 import BeautifulSoup       # to interpret the web page
from urllib.error import HTTPError
from urllib.error import URLError
import re
import post
from datetime import datetime, timezone
import pytz


session = requests.Session()
headers = {"User-Agent":"Mozilla/5.0 (X11; Linux x86_64)"
                        "AppleWebKit/537.36 (KHTML, like Gecko)"
                        "Chrome/61.0.3163.100 Safari/537.36",
           "Accept":"text/html,application/xhtml+xml,application/xml"
                    ";q=0.9,image/webp,image/apng,*/*;q=0.8"}
# url = "https://www.whatismybrowser.com/developers/what-http-headers-is-my-browser-sending"
# url = "https://www.whatismybrowser.com/detect/what-http-headers-is-my-browser-sending"
url = "https://reddit.com/r/Seattle/new"
# url = "http://www.pythonscraping.com/pages/page1.html"
# url = "https://weather.com/weather/hourbyhour/l/98203:4:US"

req = session.get(url, headers=headers)

bs_obj = BeautifulSoup(req.text, "lxml")
print(bs_obj.prettify())

# create a hash of objects (Post classes) to hold each post
Posts = post.Posts(url)

# <a class="title may-blank "
# titles = bs_obj.select('a.title.may-blank')

# <time class="live-timestamp" datetime="2017-12-02T23:38:46+00:00" title="Sat Dec 2 23:38:46 2017 UTC">
# times = bs_obj.select('live-timestamp')

# use this to parse all the info you need from the post
# <div class=" thing id
div_classes = bs_obj.find_all('div', attrs={'class': re.compile(r'thing$')})
# div_classes = bs_obj.select('[class~= thing id]')

print("*****************************")

for div in div_classes:
    print(div)

time = title = user = url = ""
comment_url = "r/Seattle/comments/"

# get everything in from first '>' to '</a>
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
        time = time_match.group(1)
        time = datetime.utcfromtimestamp(int(time[:-3]))  # convert to UTC date time
        tz = pytz.timezone('America/Los_Angeles')
        time = pytz.utc.localize(time, is_dst=None).astimezone(tz).replace(tzinfo=None)  # convert to Seattle time
    if user_match:
        user = user_match.group(1)
    if url_match:
        url = url_match.group(1)
        if comment_url in url:
            url = "https://reddit.com" + url

    Posts.add(time, title, user, url)
    time = title = user = url = ""

for count, (key, value) in enumerate(Posts.posts.items()):
    print(str(count + 1) + ") " + key)
    print("\t" + str(value.date_time_added))
    print("\t" + value.user)
    print("\t" + value.url)
