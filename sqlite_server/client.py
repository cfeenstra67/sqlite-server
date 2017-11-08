import binascii
import bson
import pandas as pd
import sqlite3
from telnetlib import Telnet

def _get_exc(name):
	if hasattr(sqlite3, name):
		return getattr(sqlite3, name)
	if isinstance(globals().get(name), Exception):
		return globals()[name]
	scope = {}
	exec('class {}(Exception): pass'.format(name), scope)
	return scope[name]

class DBClient(object):

	def __init__(self, host, key=None, port=6767):
		self.client = Telnet(host, port)
		self.client.write(str(key).encode('utf-8'))
		self._receive()

	def execute(self, statement, *args, **kwargs):
		send = bson.dumps({'components': [statement, args, kwargs]})
		send = binascii.b2a_base64(send)
		self.client.write(send)
		recv = self._receive()
		return pd.DataFrame(recv['content'])

	def _receive(self):
		recv = self.client.read_until(b'\n')
		recv = binascii.a2b_base64(recv)
		recv = bson.loads(recv)
		if recv['status_code'] == 0:
			error, msg = recv['content']
			raise _get_exc(error)(msg)
		return recv

	def close(self):
		self.client.close()

	def __enter__(self):
		pass

	def __exit__(self):
		self.close()