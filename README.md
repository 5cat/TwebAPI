# TwebAPI

This Library can be used as a replacement for the official Twitter API, it relies on mimicking the web browser requests to the twitter backend.

## Installation
```
pip install https://github.com/HashimHL/TwebAPI/archive/master.zip
```

## Usage
```python
from TwebAPI import Tapi
tapi=Tapi()
tweets=tapi.search("cats",search_type="top")
```
the tweets will be in a json format similar to the one obtained from the Twitter API.
However, not all methods can be done without login.
```python
tapi.login("username","password")
tweet=tapi.post_tweet("I like cats",media="path/to/picutre.png") # return the tweeted tweet json
```

after the first login the cookies will be saved in a file called `twitter_user_cookies` to avoid multiple logins and the phone/email verification or captcha. to change the folder path to `ciks` simply do `tapi=Tapi(cookies_path='ckis')`
and to turn off the use of cookies do `tapi.login("username","password",use_old_user_cookie=False)`

## Methods

#### login
```python
req=Tapi.login(username, password, use_old_user_cookie=False)
#username (str): can be the @screen_name or the email account or the phone number
#password (str): your password
#use_older_user_cookies (bool): whether or not to use the saved cookies for login
#returns the request object for the login
```
#### post_tweet
```python
tweet=Tapi.post_tweet(text, media=None, media_id=None, in_reply_to_status_id=None, print_log=True)
#text (str): the text of the tweet
#media (str or list): the path for the media, or a list of paths at most 4. Please check the twitter documenation https://developer.twitter.com/en/docs/media/upload-media/overview
#media_id (str or list): the media_id or a list of media_id
#in_reply_to_status_id (str or int): the tweet id that will be replied to
#print_log (bool): wether to print the status of the media being uploaded
#return the json of the tweet
```
#### upload_chunked
```python
media_info=Tapi.upload_chunked(filename,print_log=True,f=None)
#filename (str): the path of the media
#print_log (bool): wether to print the status of the media being uploaded
#f (file object): the media will be retrieved from the file object but still needs the filename for mimetype detection
#return a json object (dict) with information about the media which includes the media_id
```
#### get_tweets
```python
tweets=Tapi.get_tweets(screen_name=None,user_id=None,include_tweet_replies=False,tweet_mode='compact',count=40)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#include_tweet_replies (bool): include the replies of the user
#tweet_mode (str): you can use 'compact' to get limited information about the tweet or use 'extended' to get them all (read more in https://developer.twitter.com/en/docs/tweets/tweet-updates.html)
#count (int): the maximum number of downloaded tweets (may not be the same)
#return a list of tweets jsons from the user
```

#### get_likes
```python
tweets=Tapi.get_likes(screen_name=None,user_id=None,tweet_mode='compact',count=40)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#include_tweet_replies (bool): include the replies of the user
#tweet_mode (str): you can use 'compact' to get limited information about the tweet or use 'extended' to get them all (read more in https://developer.twitter.com/en/docs/tweets/tweet-updates.html)
#count (int): the maximum number of downloaded tweets (may not be the same)
#return a list of tweets jsons that the user liked
```
#### get_friends
```python
users=Tapi.get_friends(screen_name=None,user_id=None,count=40)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#count (int): the maximum number of downloaded users (may not be the same)
#return a list of users json that the user follow
```

#### get_followers
```python
users=Tapi.get_followers(screen_name=None,user_id=None,count=40)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#count (int): the maximum number of downloaded users (may not be the same)
#return a list of users json that follow the user
```

#### get_bookmark
```python
tweets=Tapi.get_bookmark(count=20)
#count (int): the maximum number of downloaded tweets from the bookmark
#return a list of tweets jsons from the bookmark of the logged in user
```

#### search
```python
items=Tapi.search(q,search_type='top',count=20,tweet_mode='compact')
#q (str): the query string
#search_type (str): can be one of ['top','latest','people','photos','videos']
#count (int): the number of downloaded items
#tweet_mode (str): you can use 'compact' to get limited information about the tweet or use 'extended' to get them all (read more in https://developer.twitter.com/en/docs/tweets/tweet-updates.html)
#return a list of tweet json except when search_type='people' it returns user json
```

#### users_lookup
```python
users=Tapi.users_lookup(self,screen_name=None,user_id=None)
#screen_name (str or list): the @screen_name of the user or a list of @screen_names for example ['twitter','google','facebook']
#user_id (str or list): the user id or a list of user ids
#return a user json or a list of user json that contains information about the user/users
```

#### create_favorite
```python
tweet=Tapi.create_favorite(tweet_id)
#tweet_id (str or int)
#return a json for the liked tweet
```

#### destroy_favorite
```python
tweet=Tapi.destroy_favorite(tweet_id)
#tweet_id (str or int)
#return a json for the unliked tweet
```

#### add_bookmark
```python
tweet=Tapi.add_bookmark(tweet_id)
#tweet_id (str or int)
#return a json for the bookmarked tweet
```

#### remove_bookmark
```python
tweet=Tapi.remove_bookmark(tweet_id)
#tweet_id (str or int)
#return a json for the un-bookmarked tweet
```

#### follow
```python
user=Tapi.follow(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the followed user
```

##### unfollow
```python
user=Tapi.unfollow(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the unfollowed user
```

#### mute
```python
user=Tapi.mute(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the muted user
```

#### unmute
```python
user=Tapi.unmute(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the unmuted user
```

#### block
```python
user=Tapi.block(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the blocked user
```

#### unblock
```python
user=Tapi.unblock(screen_name=None,user_id=None)
#screen_name (str): the @screen_name of the user
#user_id (str): the user id (its recomneded to use the user_id instead of the screen_name)
#return a json for the unblocked user
```

## Cursor
the Cursor class can fetch data or run function continesly
for example
```python
from TwebAPI import Cursor
users=[]
for user in Cursor(tapi.get_friends,screen_name="twitter",count=50).items(16,tqdm_bar=True):
    users.append(user)
print(len(users)==16) # True
```
you can also do it with `tapi.search` or `tapi.get_tweets` or any other method that can go back in time.
the use of `tqdm_bar=True` is just to print out the progress bar for the cursor
you can also use `.page` instead of `.items`, and the cursor will stop if it collected the required number of items or pages or if there is no more data to collect

## Additional Details
The reason behind recominding the use of `user_id` over `screen_name` is that some method can only use the `user_id` so when the `screen_name` is used a `tapi.users_lookup` will be used to get the `user_id`, and that can accumulate unnecessary requests to twitter backend.

This library should not be used for production product and its preferred to use the official Twitter API since it may voliate twitter polices https://help.twitter.com/en/rules-and-policies/twitter-automation

There is a rate limit on using some methods that can result in a temporary suspention of the service, please make sure to not run alot of method and adding `time.sleep` between calls, also using higher number of `count` in `Cursor` might help with this issue.
