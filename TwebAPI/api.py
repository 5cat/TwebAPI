from bs4 import BeautifulSoup
import requests
import os
import json
import base64
import mimetypes
import string
import random
import numpy as np
from datetime import datetime
import time
import pickle
from tqdm import tqdm
from urllib.parse import urlencode
from urllib.parse import urlparse

_BOUNDARY_CHARS = string.digits + string.ascii_letters
IMAGE_MIMETYPES = ('image/gif', 'image/jpeg', 'image/png', 'image/webp')
CHUNKED_MIMETYPES = ('image/gif', 'image/jpeg', 'image/png', 'image/webp', 'video/mp4')
VIDEO_MIMETYPES = ('video/mp4', )


def _get_media_category(is_direct_message, file_type):
	""" :reference: https://developer.twitter.com/en/docs/direct-messages/message-attachments/guides/attaching-media
		:allowed_param:
	"""
	if is_direct_message:
		prefix = 'dm'
	else:
		prefix = 'tweet'

	if file_type in IMAGE_MIMETYPES:
		if file_type == 'image/gif':
			return prefix + '_gif'
		else:
			return prefix + '_image'
	elif file_type == 'video/mp4':
		return prefix + '_video'

def _chunk_media(command, filename, max_size, form_field="media", chunk_size=4096, f=None, media_id=None, segment_index=0, is_direct_message=False):
	fp = None
	if command == 'init':
		if f is None:
			file_size = os.path.getsize(filename)
			try:
				if file_size > (max_size * 1024):
					raise Exception('File is too big, must be less than %skb.' % max_size)
			except os.error as e:
				raise Exception('Unable to access file: %s' % e.strerror)

			# build the mulitpart-formdata body
			fp = open(filename, 'rb')
		else:
			f.seek(0, 2)  # Seek to end of file
			file_size = f.tell()
			if file_size > (max_size * 1024):
				raise Exception('File is too big, must be less than %skb.' % max_size)
			f.seek(0)  # Reset to beginning of file
			fp = f
	elif command != 'finalize':
		if f is not None:
			fp = f
		else:
			raise Exception('File input for APPEND is mandatory.')

	# video must be mp4
	file_type, _ = mimetypes.guess_type(filename)

	if file_type is None:
		raise Exception('Could not determine file type')

	if file_type not in CHUNKED_MIMETYPES:
		raise Exception('Invalid file type for video: %s' % file_type)

	BOUNDARY = ''.join(random.choice(_BOUNDARY_CHARS) for i in range(30)).encode()
	body = list()
	if command == 'init':
		query = {
			'command': 'INIT',
			'media_type': file_type,
			'total_bytes': file_size,
			'media_category': _get_media_category(
				is_direct_message, file_type)
		}
		body.append(urlencode(query).encode('utf-8'))
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
		}
	elif command == 'append':
		if media_id is None:
			raise Exception('Media ID is required for APPEND command.')
		body.append(b'--' + BOUNDARY)
		body.append('Content-Disposition: form-data; name="command"'.encode('utf-8'))
		body.append(b'')
		body.append(b'APPEND')
		body.append(b'--' + BOUNDARY)
		body.append('Content-Disposition: form-data; name="media_id"'.encode('utf-8'))
		body.append(b'')
		body.append(str(media_id).encode('utf-8'))
		body.append(b'--' + BOUNDARY)
		body.append('Content-Disposition: form-data; name="segment_index"'.encode('utf-8'))
		body.append(b'')
		body.append(str(segment_index).encode('utf-8'))
		body.append(b'--' + BOUNDARY)
		body.append('Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(form_field, os.path.basename(filename)).encode('utf-8'))
		body.append('Content-Type: {0}'.format(file_type).encode('utf-8'))
		body.append(b'')
		body.append(fp.read(chunk_size))
		body.append(b'--' + BOUNDARY + b'--')
		headers = {
			'Content-Type': 'multipart/form-data; boundary={}'.format(BOUNDARY.decode())
		}
	elif command == 'finalize':
		if media_id is None:
			raise Exception('Media ID is required for FINALIZE command.')
		body.append(
			urlencode({
				'command': 'FINALIZE',
				'media_id': media_id
			}).encode('utf-8')
		)
		headers = {
			'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
		}

	body = b'\r\n'.join(body)
	# build headers
	headers['Content-Length'] = str(len(body))

	return headers, body, fp

class Tapi:

	def __init__(self,cookies_path='twitter_user_cookies',user_cookies_save_intervals=60):
		self.sess=requests.Session()
		self.headers={
			'authority':'twitter.com',
			'scheme': 'https',
			'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
			'accept-encoding':'gzip, deflate',
			'content-type':'application/x-www-form-urlencoded',
			'origin':'https://twitter.com',
			'cache-control':'no-cache',
			'pragma':'no-cache',
			'upgrade-insecure-requests':'1',
			'user-agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
			}
		self.is_login=False
		self.cookies_path=cookies_path
		self.user_cookies_save_intervals=user_cookies_save_intervals
		self.last_time_user_cookies_saved=-np.inf

	def sess_handler(self,link,OPTIONS=False,use_auth=False,**kwargs):
		data=kwargs.pop('data',None)
		params=kwargs.pop('params',None)
		method=kwargs.pop('method','GET').upper()
		urlprs=urlparse(link)
		authority=urlprs.netloc
		path=urlprs.path
		dict_headers=kwargs.pop("dict_headers",{})
		if OPTIONS:
			headers=self.get_headers(
				dict_headers={
				'access-control-request-headers':'authorization,x-csrf-token,x-twitter-active-user,x-twitter-auth-type',
				'access-control-request-method':method},
				authority=authority,
				path=path,
				method='OPTIONS',
				)
			r = self.sess.options(link,headers=headers)
			self.save_cookies()
		if use_auth:
			kwargs['authorization']=kwargs.pop('authorization'
				,'Bearer AAAAAAAAAAAAAAAAAAAAAPYXBAAAAAAACLXUNDekMxqa8h%2F40K4moUkGsoc%3DTYfbDKbT3jJPCEVnMYqilB28NHfOPqkca3qaAxGfsyKCs0wRbw')
			
			a_dict_auth={
			'x-csrf-token':self.sess.cookies['ct0'],
			'x-twitter-active-user':'yes',
			'x-twitter-auth-type':'OAuth2Session'
			}
			dict_headers={**dict_headers,**a_dict_auth}


		headers=self.get_headers(
				authority=authority,path=path,method=method,dict_headers=dict_headers,
				**kwargs
				)
		if method=='GET':
			r=self.sess.get(link,headers=headers,data=data,params=params)
		elif method=='POST':
			r=self.sess.post(link,headers=headers,data=data,params=params)
		else:
			raise Exception("the options are GET and POST for the methods")

		self.save_cookies()
		try:
			res_json=r.json()
		except:
			res_json=None

		if res_json:
			if ('errors' in res_json) or ('error' in res_json):
				raise Exception(str(res_json))
			elif ('response' in res_json):
				if 'errors' in res_json['response']:
					if len(res_json['response']['errors'])>0:
						raise Exception(res_json['response']['errors'])
		return r

	def upload_chunked(self,filename,print_log=True,**kwargs):
		""" :reference https://dev.twitter.com/rest/reference/post/media/upload-chunked
			:allowed_param:
		"""
		f = kwargs.pop('file', None)
		file_type, _ = mimetypes.guess_type(filename)
		max_size_chunked = 15360
		def temp_func(x,**kwargs):
			return x

		if print_log:
			tqdm_f=tqdm
		else:
			tqdm_f=temp_func

		if file_type in VIDEO_MIMETYPES:
			max_size_chunked*= 23

		# Media category is dependant on whether media is attached to a tweet
		# or to a direct message. Assume tweet by default.
		is_direct_message = kwargs.pop('is_direct_message', False)

		# Initialize upload (Twitter cannot handle videos > 15 MB)
		headers, post_data, fp = _chunk_media('init', filename, max_size_chunked, form_field='media', f=f, is_direct_message=is_direct_message)

		# Send the INIT request
		link='https://upload.twitter.com/i/media/upload.json'
		res=self.sess_handler(link,dict_headers=headers,data=post_data,method='POST',accept='*/*')
		if print_log:
			print("INIT",res.status_code)
		media_info=res.json()

		# If a media ID has been generated, we can send the file
		if media_info['media_id']:
			# default chunk size is 1MB, can be overridden with keyword argument.
			# minimum chunk size is 16K, which keeps the maximum number of chunks under 999
			chunk_size = kwargs.pop('chunk_size', 1024 * 1024)
			chunk_size = max(chunk_size, 16 * 2014)
			if f is None:
				fsize = os.path.getsize(filename)
			else:
				fsize = os.fstat(f.fileno()).st_size

			nloops = int(fsize / chunk_size) + (1 if fsize % chunk_size > 0 else 0)
			for i in tqdm_f(range(nloops),desc='APPEND'):
				headers, post_data, fp = _chunk_media('append', filename, max_size_chunked, chunk_size=chunk_size, f=fp, media_id=media_info['media_id'], segment_index=i, is_direct_message=is_direct_message)
				# The APPEND command returns an empty response body
				res=self.sess_handler(link,dict_headers=headers,data=post_data,method='POST',accept='*/*')
				# media_info=json.loads(res.text)
			# When all chunks have been sent, we can finalize.
			headers, post_data, fp = _chunk_media('finalize', filename, max_size_chunked, media_id=media_info['media_id'], is_direct_message=is_direct_message)

			# The FINALIZE command returns media information
			res=self.sess_handler(link,dict_headers=headers,data=post_data,method='POST',accept='*/*')

			if print_log:
				print("FINALIZE",res.status_code)
			media_info=res.json()
			if 'processing_info' in media_info:
				progress=media_info['processing_info']
				if print_log:
					tqdm_bar=tqdm_f(desc='STATUS',total=100)
				old_n=0
				while True:
					time.sleep(progress['check_after_secs'])			
					params={
						'command':'STATUS',
						'media_id':media_info['media_id']
						}
					res=self.sess_handler(link,params=params,method='GET',accept='*/*')
					media_info=res.json()
					progress=media_info['processing_info']
					current_n=progress.get('progress_percent',0)
					if print_log:
						tqdm_bar.update(current_n-old_n)
					old_n=current_n
					#print("STATUS progress",progress['progress_percent'])
					if progress['state']=='succeeded':
						if print_log:
							tqdm_bar.close()
						break

			return media_info
		else:
			return media_info

	def get_headers(self,dict_headers=None,**kwargs):
		dict_headers={} if dict_headers is None else dict_headers
		headers={**{**self.headers,**kwargs},**dict_headers}
		return headers

	def get_authenticity_token(self):
		r = self.sess_handler("https://twitter.com")
		soup = BeautifulSoup(r.text,"lxml")
		self.authenticity_token = soup.select_one("[name='authenticity_token']")['value']
		return self.authenticity_token

	def get_user_info(self,screen_name):
		link='https://api.twitter.com/graphql/5CddI_T_Pvpfk1jvnGbw0g/UserByScreenName'
		variables={"screen_name":screen_name,"withHighlightedLabel":True}
		params={'variables':json.dumps(variables)}
		res=self.sess_handler(link,method='GET',use_auth=True,params=params)
		return res.json()

	def login(self,username,password,use_old_user_cookie=True):
		self.username=username
		try:
			old_cookies=os.listdir(self.cookies_path)
		except FileNotFoundError:
			os.mkdir(self.cookies_path)
			old_cookies=[]
		if (username in old_cookies) and use_old_user_cookie:
			print('info: cookies will be used')
			with open('{}/{}'.format(self.cookies_path,username),'rb') as fp:
				cookies=pickle.load(fp)

			self.sess.cookies=cookies
			#headers=self.get_headers()
			self.is_login=True
			self.get_authenticity_token()
			return self.sess_handler("https://twitter.com/google/with_replies")#self.sess.get("https://twitter.com/google/with_replies",headers=headers)

		payload={
			'session[username_or_email]':username,
			'session[password]':password,
			'authenticity_token':self.get_authenticity_token(),
			'ui_metrics':'{"rf":{"a089f97643a8f781347b24fdee1370c684de744577338c48604595c6deff739f":248,"aff1c124cd2aac5c914ce8d9b0abd2977fa94a47e782c4b4b10bf735dd54ef24":38,"abcadc5222b1b62ef52b21d7ea3cb340c98b92975b8ffe9603199df80b92d17e":144,"b5ed1a9aec5ac7a9022363830fe85d0265e117ce101f02f3b78cd177d5e3e6cc":-129},"s":"tS-KJKqvlWLWPWrEYadFFsBkKEHqVaOnyQDorJ-93Hc323EjMZVS90zxrC8psSnZfGKy_kK296B4BPjIgmaeocnPW5KqmLdiwvk3opOwnsVgsv5knFBIB6bvKDSjcfvgb_OiFJ-kW5-BE8AVixnJW-yABXecZmcMxO6lHSEtfZ0S4FKI5S6YMJQFHilDGFDC5dlvSEalh08-ihXpNG-H8LEllurcKySmIzaJRj3NMw7S2Q18gU_GbMc1RIQbguJybhU2jekPPR6AmOjx9lSwhrKWKU5KiHC2e4fCR_SmDCtoOd186HxeBZU9MmqiKhzuXEewWHlVJeDIaL8kYOKJCwAAAWnvMSXy"}',
			'scribe_log':'',
			'redirect_after_login':'',
				}

		self.last_time_user_cookies_saved=time.time()
		res=self.sess_handler("https://twitter.com/sessions",data=payload,method='POST')
		self.is_login=True
		return res

	def save_cookies(self):
		if (time.time()-self.last_time_user_cookies_saved)>self.user_cookies_save_intervals:
			with open('{}/{}'.format(self.cookies_path,self.username),'wb') as fp:
				pickle.dump(self.sess.cookies,fp)

	def check_if_user_id(self,user_id):
		try:
			int(user_id)
		except:
			raise Exception("Please provide the user twitter ID not the screen_name")

	def add_user_id_screen_name_params(self,dict_,screen_name=None,user_id=None,accept_screen_name=True):
		if accept_screen_name and screen_name:
			dict_['screen_name']=screen_name
		elif (not accept_screen_name) and screen_name:
			try:
				user_id=self.get_user_info(screen_name)['data']['user']['rest_id']
			except Exception as e:
				print("warining!: Tapi.get_user_info method faild, will use Tapi.user_lookup method instead")
				user_id=self.users_lookup(screen_name=screen_name)['id_str']
			dict_['user_id']=user_id
			return user_id
		elif user_id:
			dict_['user_id']=user_id
		else:
			raise Exception("Please provide either the screen_name or the user_id")

	def _add_more_params(self,dict_,**kwargs):
		additional_available_params=['include_profile_interstitial_type', 'include_blocking', 'include_blocked_by',
									 'include_followed_by', 'include_want_retweets', 'include_mute_edge', 'include_can_dm',
									 'include_can_media_tag', 'skip_status', 'cards_platform', 'include_cards',
									 'include_composer_source', 'include_ext_alt_text', 'include_reply_count', 'tweet_mode',
									 'include_entities', 'include_user_entities', 'include_ext_media_color', 'include_ext_media_availability',
									 'send_error_codes', 'q', 'count', 'query_source', 'pc', 'spelling_corrections', 'ext',
									 'user_id', 'userId', 'screen_name']
		for key,value in kwargs.items():
			if key in additional_available_params:
				dict_[key]=value
		return dict_

	def check_if_login(self):
		if not self.is_login:
			raise Exception("This method require authentication, Please login using the Tapi.login method")

	def tweet_json_2_handeler(self,res_json):
		if len(res_json['timeline']['instructions'])>0:
			sortIndexes = dict()
			for entri in res_json['timeline']['instructions'][-1]['addEntries']['entries']:
				try:
					id_=entri['content']['item']['content']['tweet']['id']
					sortindex=int(entri['sortIndex'])
					sortIndexes[id_]=sortindex
				except KeyError:
					try:
						cursor=entri['content']['operation']['cursor']
						if cursor['cursorType']=='Bottom':
							cursor_value=cursor['value']
					except KeyError:
						pass

			_tweets = res_json['globalObjects']['tweets']
		else:
			_tweets= dict()
		key_func=lambda x:sortIndexes[x['id_str']]
		_tweets_sorted = sorted([tweet for tweet in _tweets.values() if tweet['id_str'] in sortIndexes],key=key_func,reverse=True)
		tweets=[]
		for tweet in _tweets_sorted:
			tweet['user']=res_json['globalObjects']['users'][str(tweet['user_id'])]
			tweet['sortIndex']=sortIndexes[tweet['id_str']]
			if 'quoted_status_id_str' in tweet:
				try:
					tweet['quoted_status']=_tweets[tweet['quoted_status_id_str']]
				except KeyError:
					pass
			if 'retweeted_status_id_str' in tweet:
				try:
					tweet['retweeted_status']=_tweets[tweet['retweeted_status_id_str']]
				except KeyError:
					pass
			tweets.append(tweet)
		return tweets,cursor_value

	def user_json_2_handeler(self,res_json):
		if len(res_json['timeline']['instructions'])>0:
			sortIndexes = dict()
			for entri in res_json['timeline']['instructions'][-1]['addEntries']['entries']:
				try:
					id_=entri['content']['item']['content']['user']['id']
					sortindex=int(entri['sortIndex'])
					sortIndexes[id_]=sortindex
				except KeyError:
					try:
						cursor=entri['content']['operation']['cursor']
						if cursor['cursorType']=='Bottom':
							cursor_value=cursor['value']
					except KeyError:
						pass

			_users = res_json['globalObjects']['users']
		else:
			_users= dict()

		key_func=lambda x:sortIndexes[x['id_str']]
		_users_sorted = sorted([user for user in _users.values() if user['id_str'] in sortIndexes],key=key_func,reverse=True)
		users=[]
		for user in _users_sorted:
			user['sortIndex']=sortIndexes[user['id_str']]
			users.append(user)
		return users,cursor_value

	def post_tweet(self,text,media=None,media_id=None,in_reply_to_status_id=None,**kwargs):

		if (not (media_id is None)) and (not (media is None)):
			raise Exception("Please ethier provide media_id or media not both")

		if media is None:
			media=[]
		elif type(media)==str:
			media=[media]
		elif type(media)==list:
			media=media
		else:
			raise Exception("Dessspaaaa ceto")

		if media_id is None:
			media_ids=[]
			for filepath in media:
				res_json=self.upload_chunked(filepath,**kwargs)
				media_ids.append(str(res_json['media_id']))
		elif type(media_id) in [str,int]:
			media_ids=[str(media_id)]
		elif type(media_id)==list:
			media_ids=list(map(str,media_id))

		data={"batch_mode":'off',"status":text}

		data['media_ids']=','.join(media_ids)
		if in_reply_to_status_id:
			data['in_reply_to_status_id']=in_reply_to_status_id

		link="https://api.twitter.com/1.1/statuses/update.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data=data)
		return r

	def get_tweets(self,screen_name=None,user_id=None,include_tweet_replies=False,tweet_mode='compact',count=40,cursor_value=None,is_cursor=False,**kwargs):
		if include_tweet_replies:
			self.check_if_login()
		params=dict()
		user_id=self.add_user_id_screen_name_params(params,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		self._add_more_params(params,**kwargs)
		link='https://api.twitter.com/2/timeline/profile/{}.json'.format(user_id)
		params['count']=count
		params['include_tweet_replies']=include_tweet_replies
		params['tweet_mode']=tweet_mode
		if cursor_value:
			params['cursor']=cursor_value
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()
		tweets,cursor_value=self.tweet_json_2_handeler(res_json)
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',tweets
		else:
			return tweets

	def get_likes(self,screen_name=None,user_id=None,tweet_mode='compact',count=40,cursor_value=None,is_cursor=False,**kwargs):
		self.check_if_login()
		params=dict()
		user_id=self.add_user_id_screen_name_params(params,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		self._add_more_params(params,**kwargs)
		link='https://api.twitter.com/2/timeline/favorites/{}.json'.format(user_id)
		params['count']=count
		params['tweet_mode']=tweet_mode
		if cursor_value:
			params['cursor']=cursor_value
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()
		tweets,cursor_value=self.tweet_json_2_handeler(res_json)
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',tweets
		else:
			return tweets

	def get_friends(self,screen_name=None,user_id=None,count=40,cursor_value=None,is_cursor=False):
		self.check_if_login()
		link='https://api.twitter.com/1.1/friends/list.json'
		params=dict()
		self.add_user_id_screen_name_params(params,screen_name=screen_name,user_id=user_id,accept_screen_name=True)
		params['count']=count
		if cursor_value:
			params['cursor']=cursor_value
		else:
			params['cursor']=-1
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()
		cursor_value=res_json['next_cursor']
		users=res_json['users']
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',users
		else:
			return users

	def get_followers(self,screen_name=None,user_id=None,count=40,cursor_value=None,is_cursor=False):
		self.check_if_login()
		link='https://api.twitter.com/1.1/followers/list.json'
		params=dict()
		self.add_user_id_screen_name_params(params,screen_name=screen_name,user_id=user_id,accept_screen_name=True)
		params['user_id']=user_id
		params['count']=count
		if cursor_value:
			params['cursor']=cursor_value
		else:
			params['cursor']=-1
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()				
		cursor_value=res_json['next_cursor']
		users=res_json['users']
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',users
		else:
			return users

	def get_bookmark(self,count=20,cursor_value=None,is_cursor=False):
		self.check_if_login()
		link='https://api.twitter.com/2/timeline/bookmark.json'
		params=dict()
		params['count']=count
		if cursor_value:
			params['cursor']=cursor_value
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()
		tweets,cursor_value=self.tweet_json_2_handeler(res_json)
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',tweets
		else:
			return tweets	

	def search(self,q,search_type='top',count=20,tweet_mode='compact',cursor_value=None,is_cursor=False,**kwargs):
		link='https://api.twitter.com/2/search/adaptive.json'
		params=dict()
		params['q']=q
		params['count']=count
		allowed_param_for_search_type=['top','latest','people','photos','videos']
		if not (search_type in allowed_param_for_search_type):
			raise Exception('search_type should have one of these {} not {}'.format(allowed_param_for_search_type,search_type))
		if search_type=='latest':
			params['tweet_search_mode']='live'

		elif search_type=='people':
			params['result_filter']='user'

		elif search_type=='photos':
			params['result_filter']='image'

		elif search_type=='videos':
			params['result_filter']='video'


		self._add_more_params(params,**kwargs)
		if cursor_value:
			params['cursor']=cursor_value
		r = self.sess_handler(link,method='GET',use_auth=True,
			params=params)
		res_json = r.json()
	
		if search_type=='people':
			res_items,cursor_value=self.user_json_2_handeler(res_json)
		else:	
			res_items,cursor_value=self.tweet_json_2_handeler(res_json)
		has_more=True
		if is_cursor:
			return has_more,cursor_value,'cursor_value',res_items
		else:
			return res_items

	def users_lookup(self,screen_name=None,user_id=None,include_entities=False,tweet_mode='compact'):
		if screen_name and user_id:
			raise Exception('Provide either the screen_name or user_id')
		if screen_name:
			values=screen_name
			values_name='screen_name'
		else:
			values=user_id
			values_name='user_id'

		if type(values)==str:
			values=[values]
		elif type(values)==list:
			values=values
		else:
			raise Exception("the type of the data should be either a list or a string")

		values=','.join(values)
		link='https://api.twitter.com/1.1/users/lookup.json'
		data=dict()
		data[values_name]=values
		data['include_entities']=include_entities
		data['tweet_mode']=tweet_mode
		r = self.sess_handler(link,method='POST',use_auth=True,
			data=data)
		res_json = r.json()
		return res_json if len(res_json)>1 else res_json[0]

	def create_favorite(self,tweet_id):
		self.check_if_login()
		link="https://api.twitter.com/1.1/favorites/create.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data={'id':tweet_id})
		return r.json()

	def destroy_favorite(self,tweet_id):
		self.check_if_login()
		link="https://api.twitter.com/1.1/favorites/destroy.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data={'id':tweet_id})
		return r.json()

	def add_bookmark(self,tweet_id):
		self.check_if_login()
		link="https://api.twitter.com/1.1/bookmark/entries/add.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data={'tweet_id':tweet_id})
		return r.json()

	def remove_bookmark(self,tweet_id):
		self.check_if_login()
		link="https://api.twitter.com/1.1/bookmark/entries/remove.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data={'tweet_id':tweet_id})
		return r.json()

	def follow(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=True)
		link="https://api.twitter.com/1.1/friendships/create.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data=data)
		return r.json()

	def unfollow(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=True)
		link="https://api.twitter.com/1.1/friendships/destroy.json"
		r = self.sess_handler(link,method='POST',use_auth=True,
			data=data)
		return r.json()

	def mute(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		data['authenticity_token']=self.authenticity_token
		link="https://twitter.com/i/user/mute"
		r = self.sess_handler(link,method='POST',
			data=data)
		return r.json()

	def unmute(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		data['authenticity_token']=self.authenticity_token
		link="https://twitter.com/i/user/unmute"
		r = self.sess_handler(link,method='POST',
			data=data)
		return r.json()


	def block(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		data['authenticity_token']=self.authenticity_token
		link="https://twitter.com/i/user/block"
		r = self.sess_handler(link,method='POST',
			data=data)
		return r.json()

	def unblock(self,screen_name=None,user_id=None):
		self.check_if_login()
		data=dict()
		self.add_user_id_screen_name_params(data,screen_name=screen_name,user_id=user_id,accept_screen_name=False)
		data['authenticity_token']=self.authenticity_token
		link="https://twitter.com/i/user/unblock"
		r = self.sess_handler(link,method='POST',
			data=data)
		return r.json()