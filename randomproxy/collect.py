from collections import namedtuple, defaultdict
import requests
import itertools
from bs4 import BeautifulSoup
from datetime import datetime
import shelve
import warnings
from concurrent.futures import ThreadPoolExecutor


from .config import CACHE_PATH
from .exceptions import PageServerDown


class Proxy:

	__slots__ = ('ip', 'port', 'type', 'anonymous', 'speed', 'time_since_last_check')

	def __init__(self, ip, port, type, anonymous, speed, time_since_last_check):
		self.ip = ip
		self.port = port
		self.type = type
		self.anonymous = anonymous
		self.speed = speed
		self.time_since_last_check = time_since_last_check

	def to_string(self):
		return '{}:{}'.format(self.ip, self.port)

	__repr__ = __str__ = to_string

	def __eq__(self, other):
		return self.to_string() == other.to_string()

	def __hash__(self):
		return hash(self.to_string())


def parse_page(url):
	""" Parse a single html page on https://www.xicidaili.com to get a list of proxies """
	now = datetime.today()

	headers = headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
	page = requests.get(url, headers=headers)
	if page.status_code != 200:
		warnings.warn('{} could not be connected at the moment'.format(url))
		# raise PageServerDown('{} could not connect'.format(url))
	soup = BeautifulSoup(page.text, 'lxml')

	proxies = list()
	for row in soup.find_all('tr'):
		cols = row.find_all('td')
		if len(cols) == 10:
			speed = cols[6].find(class_='bar_inner').attrs['style']  # width:99%
			speed = float(''.join(filter(lambda x: x.isdigit(), speed)))

			last_check_time = datetime.strptime(cols[-1].text.strip(), '%y-%m-%d %H:%M')
			time_since_last_check = (now - last_check_time).seconds

			p = Proxy(ip=cols[1].text, 
					port=cols[2].text, 
					type=cols[5].text, 
					anonymous=(cols[4].text=='高匿'), 
					speed=speed,
					time_since_last_check=time_since_last_check)
			proxies.append(p)
	return proxies


def get_proxies(use_cache=False, save=True):
	# TODO: http://www.kuaidaili.com/free/inha/

	if use_cache:
		# set flag to 'r' to support concurrent reads
		with shelve.open(CACHE_PATH, flag='r') as f:
			proxies = {k: v for k, v in f.items()}
			return proxies

	XICI = 'https://www.xicidaili.com/{}/{}'

	proxies = defaultdict(list)
	# get the first 10 pages
	# for url in [XICI.format(*i) for i in itertools.product(['wn', 'wt'], range(1, 11))]:
	# 	for proxy in parse_page(url):
	# 		proxies[proxy.type].append(proxy)

	with ThreadPoolExecutor(max_workers=20) as ex:
		results = ex.map(parse_page, 
			[XICI.format(*i) for i in itertools.product(['wn', 'wt'], range(1, 11))])

	for result in results:
		for proxy in result:
			proxies[proxy.type].append(proxy)

	if save:
		# TODO: adding thread locks here
		with shelve.open(CACHE_PATH, writeback=True) as f:
			for k, v in proxies.items():
				f[k] = v
		print('Saved to {}'.format(CACHE_PATH))
	return proxies


