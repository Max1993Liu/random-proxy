import random
from datetime import datetime
from operator import attrgetter

from .collect import get_proxies
from .exceptions import *


class ProxyPool:

	def __init__(self, use_cache=True, update_interval=600):
		""" 
		:param update_interval: Number of seconds between automatic update, 
			set to None to disable automatic update
		"""
		self.proxies = get_proxies(use_cache=use_cache)
		self.update_interval = update_interval
		self.last_update_time = datetime.now()

	def get_latest(self, type='HTTP'):
		self.check_update()
		return sorted(self.proxies[type.upper()], key=attrgetter('time_since_last_check'))[0]

	def get_fastest(self, type='HTTP'):
		self.check_update()
		# pick the lastest proxy with fastest speed
		return sorted(self.proxies[type.upper()], key=lambda x: (-x.speed, x.time_since_last_check))[0]

	def get_random(self, type='HTTP', max_age=600):
		""" Choose a random Proxy with at most {max_age} seconds since last check """
		self.check_update()
		candidates = [p for p in self.proxies[type.upper()] if p.time_since_last_check <= max_age]
		if len(candidates) == 0:
			raise NoProxyAvailable('No {} proxy has been active within last {} seconds.'.format(type, max_age))
		return random.choice(candidates)

	def check_update(self):
		if self.update_interval is not None and \
			(datetime.now() - self.last_update_time).seconds >= self.update_interval:
			print('Updateing proxies.')
			self.proxies = get_proxies(use_cache=False, save=True)
			self.last_update_time = datetime.now()

	get = get_latest