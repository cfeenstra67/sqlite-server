import argparse
import atexit
import binascii
import bson
from datetime import datetime
import hashlib
from multiprocessing import Lock
import os
from .permissions import setup_key_table, unlock_key_table, lock_key_table
import re
import sqlite3
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

DB_DEFAULT = os.path.expanduser('~/server.db')

def serialize(data):
	bindata = bson.dumps(data)
	return binascii.b2a_base64(bindata)

def deserialize(data):
	bindata = binascii.a2b_base64(data)
	return bson.loads(bindata)

class BadRequest(Exception):
	pass

class Logger(object):
	def __init__(self, verbose=True):
		self.verbose = verbose

	def log(self, *args, **kwargs):
		if self.verbose:
			print(
				'[{}]'.format(type(self).__name__),
				datetime.now().strftime('%F %T:'),
				*args,
				**kwargs
			)

class StartupLogger(Logger):
	pass

class ExitLogger(Logger):
	pass

class QueryHandler(object):

	def __init__(self, conn, lock):
		self.conn = conn
		self.lock = lock

	def validate_query(self, query):
		updating = re.search(r'TRIGGER.+update_keys', query, re.I | re.S)
		inserting = re.search(r'TRIGGER.+insert_keys', query, re.I | re.S)
		deleting = re.search(r'TRIGGER.+delete_keys', query, re.I | re.S)
		dropping = re.search(r'DROP\s+TABLE.+REMOTE_ACCESS_KEYS', query, re.I | re.S)
		if any([updating, inserting, deleting, dropping]):
			raise sqlite3.IntegrityError('Enough of that, please.')

	def handle_query(self, query):
		curs = self.conn.cursor()
		try:
			with self.lock:
				try:
					try:
						query, args, kwargs = deserialize(query)['components']
					except:
						raise BadRequest('Unable to deserialize data.')

					self.validate_query(query)
					curs.execute(query, *args, **kwargs)
					self.conn.commit()
				except Exception as exc:
					fetched = {'status_code': 0, 'content': [type(exc).__name__, str(exc)]}
				else:
					fetched = curs.fetchall()
					fetched = [{k: row[k] for k in row.keys()} for row in fetched]
					fetched = {'status_code': 1, 'content': fetched}
				return fetched
		finally:
			curs.close()

	def authenticate(self, key):
		hashed_key = hashlib.sha256(key).hexdigest()
		curs = self.conn.cursor()
		try:
			with self.lock:
				curs.execute('SELECT * FROM REMOTE_ACCESS_KEYS WHERE key=?', (hashed_key,))
				if curs.fetchone():
					return {'status_code': 1, 'content': None}
				curs.execute('SELECT count(*) FROM REMOTE_ACCESS_KEYS')
				if curs.fetchone()[0]:
					return {'status_code': 0, 'content': ['IntegrityError', 'Authentication Failed.']}
				else:
					return {'status_code': 1, 'content': None}
		finally:
			curs.close()

class ConnectionProtocol(Protocol, Logger):

	def __init__(self, factory, addr):
		self.factory = factory
		self.verbose = self.factory.verbose
		self.addr = addr
		self.authenticated = False

	def connectionMade(self):
		self.factory.numProtocols += 1
		self.log('Connection made to {}. {} active'.format(self.addr.host, self.factory.numProtocols))

	def connectionLost(self, reason):
		self.factory.numProtocols -= 1
		self.log('{} ({}) {} active'.format(
			reason.getErrorMessage(), 
			self.addr.host, 
			self.factory.numProtocols
		))

	def dataReceived(self, data):
		self.log('Data Received from {}.'.format(self.addr.host))
		handler = QueryHandler(self.factory.conn, self.factory.lock)
		if self.authenticated:
			send = handler.handle_query(data)
			self.transport.write(serialize(send))
		else:
			auth = handler.authenticate(data)
			send = serialize(auth)
			self.transport.write(send)
			if auth['status_code']:
				self.log('{} Authenticated Successfully.'.format(self.addr.host))
				self.authenticated = True
			else:
				self.log('Authenicated failed for {}. Losing Connection.'.format(self.addr.host))
				self.transport.loseConnection()

class ConnectionFactory(Factory, Logger):
	def __init__(self, conn, verbose=True):
		self.verbose = verbose
		self.conn = conn
		self.lock = Lock()
		self.numProtocols = 0

	def buildProtocol(self, addr):
		self.log('Instantiating connection from {}'.format(addr.host))
		return ConnectionProtocol(self, addr)

def create_connection(dbpath):
	conn = sqlite3.connect(dbpath)
	conn.row_factory = sqlite3.Row
	setup_key_table(conn)
	lock_key_table(conn)
	return conn

def run(conn, port, verbose=True):
	reactor.listenTCP(port, ConnectionFactory(conn, verbose))

	StartupLogger(verbose).log('Starting server.')
	@atexit.register
	def exit():
		ExitLogger(verbose).log('Stopping server.')
		conn.close()

	reactor.run()

def keygen(conn):
	key = binascii.b2a_hex(os.urandom(16))
	hashed_key = hashlib.sha256(key).hexdigest()

	unlock_key_table(conn)
	curs = conn.cursor()
	try:
		curs.execute('INSERT INTO REMOTE_ACCESS_KEYS VALUES (?)', (hashed_key,))
	finally:
		curs.close()
		conn.commit()
	lock_key_table(conn)

	print(key.decode('ascii'))

if __name__ == '__main__':

	parser = argparse.ArgumentParser()
	parser.add_argument('action')
	parser.add_argument('db', nargs='?', default=DB_DEFAULT,
		help='path of database file')
	parser.add_argument('-p', '--port', type=int, default=6767)
	parser.add_argument('-v', '--verbose', action='store_true')

	args = parser.parse_args()
	conn = create_connection(args.db)
	if args.action == 'run':
		run(conn, args.port, args.verbose)
	elif args.action == 'keygen':
		keygen(conn)
	else:
		print('Invalid action.')
		conn.close()
