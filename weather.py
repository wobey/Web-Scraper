import os


class Climate(object):
    def __init__(self, unique_id, date_time, temp, wind, phrase):
        self.unique_id = unique_id     # e.g. key id could be title + time
        self.date_time = date_time
        self.temp = temp
        self.wind = wind
        self.phrase = phrase


# TODO create a static or singleton object
# TODO use decorators to easily add Post objects (and check for their existance)
class Weather(object):
    def __init__(self, name):
        self.name = name    # name of subreddit that is currently being scrapped
        self.weather = {}

    def add(self, date_time, temp, wind, phrase):
        self.weather.update({date_time: Climate(date_time, date_time, temp, wind, phrase)})
