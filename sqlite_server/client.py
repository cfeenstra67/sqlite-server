import binascii
import pandas as pd
import pickle
from telnetlib import Telnet

class DBClient(object):

	def __init__(self, host, port):
		self.client = Telnet(host, port)

	def execute(self, statement, *args, **kwargs):
		send = binascii.b2a_base64(pickle.dumps((statement, args, kwargs)))
		self.client.write(send)
		recv = self.client.read_until(b'\n')
		recv = pickle.loads(binascii.a2b_base64(recv))
		if isinstance(recv, Exception):
			raise recv
		return pd.DataFrame(recv)

	def close(self):
		self.client.close()

	def __enter__(self):
		pass

	def __exit__(self):
		self.close()