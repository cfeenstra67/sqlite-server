import argparse
import atexit
import binascii
from datetime import datetime
import sqlite3
from multiprocessing import Lock
import os
import pickle
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor

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

	def handle_query(self, query):
		curs = self.conn.cursor()
		try:
			with self.lock:
				try:
					query, args, kwargs = pickle.loads(binascii.a2b_base64(query))
					curs.execute(query, *args, **kwargs)
					self.conn.commit()
				except Exception as exc:
					fetched = exc
				else:
					fetched = curs.fetchall()
					fetched = [{k: row[k] for k in row.keys()} for row in fetched]
				return binascii.b2a_base64(pickle.dumps(fetched))
		finally:
			curs.close()

class ConnectionProtocol(Protocol, Logger):

	def __init__(self, factory):
		self.factory = factory
		self.verbose = self.factory.verbose

	def connectionMade(self):
		self.factory.numProtocols += 1
		self.log('Connection Made. {} active'.format(self.factory.numProtocols))

	def connectionLost(self, reason):
		self.factory.numProtocols -= 1
		self.log('{} {} active'.format(reason.getErrorMessage(), self.factory.numProtocols))

	def dataReceived(self, data):
		self.log('Data Received.')
		handler = QueryHandler(self.factory.conn, self.factory.lock)
		self.transport.write(handler.handle_query(data))

class ConnectionFactory(Factory, Logger):
	def __init__(self, conn, verbose=True):
		self.verbose = verbose
		self.conn = conn
		self.lock = Lock()
		self.numProtocols = 0

	def buildProtocol(self, addr):
		self.log('Instantiating connection from {}'.format(addr))
		return ConnectionProtocol(self)


def run(dbpath, port, verbose=True):
	conn = sqlite3.connect(dbpath)
	conn.row_factory = sqlite3.Row
	reactor.listenTCP(port, ConnectionFactory(conn, verbose))

	if verbose:
		StartupLogger().log('Starting server.')
		@atexit.register
		def exit():
			ExitLogger().log('Stopping server.')
			conn.close()

	reactor.run()

if __name__ == '__main__':
	db_default = os.path.join(*os.path.split(__file__)[:-1], 'server.db')

	parser = argparse.ArgumentParser()
	parser.add_argument('db', nargs='?', default=db_default,
		help='path')
	parser.add_argument('-p', '--port', nargs=1, type=int, default=6767)
	parser.add_argument('-v', '--verbose', action='store_true')

	args = parser.parse_args()
	run(args.db, args.port, args.verbose)