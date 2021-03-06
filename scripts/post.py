class Post(object):
    def __init__(self, unique_id, date_time, title, user, url):
        self.unique_id = unique_id     # e.g. key id could be title + time
        self.date_time = date_time
        self.title = title
        self.user = user
        self.url = url


# TODO create a static or singleton object
# TODO use decorators to easily add Post objects (and check for their existance)
class Posts(object):
    def __init__(self, name):
        self.name = name    # name of subreddit that is currently being scrapped
        self.posts = {}

    def add(self, date_time, title, user, url):
        # either add to the dictionary of posts, or update
        if title not in self.posts:
            # create Post object
            self.posts.update({title: Post(title, date_time, title, user, url)})
