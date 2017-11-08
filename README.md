This is a little project, mostly as a little projected to use the Twisted framework and write a server. It's not intended to be used, certainly not in a production environment.

That said, to test out this project either clone the repo and run the setup script or simply install using `pip3 install git+https://github.com/cfeenstra67/sqlite-server.git` (written in Python 3).

To run the database server, run the following command: `python3 -m sqlite_server.server [DB_PATH] [-p PORT] [-v]`. It's recommended that you use the `-v` argument to see what's going on. The default port is 6767, and the default db path is `~/server.db`

When the server is running, you can connect to the server as follows:
```
from sqlite_server.client import DBClient
db = DBClient('localhost', 6767)
db.execute('CREATE TABLE test (name varchar)')
...
db.close()
```

You can also use the database client as a context manager, for example:
```
with DBClient('localhost', 6767) as db:
	db.execute('CREATE TABLE test (name varchar)')
```
The API for the database client is extremely simple, and does not follow the Python DB API protocol. The only method used to interact with the database is `execute(query, *args, **kwargs)`, and this will always either return a pandas dataframe with the results (even if the query is something that does not return any sort of result, such as an INSERT statement; in this case it will just return an empty dataframe) or raise an exception. Data is transmitted between the server and the client as base64 encoded, pickled Python objects (another reason this server isn't suitable for almost any use cases), so exceptions raised by sqlite on the server side are transmitted in this form and raised on the client side.

Check out my blog post about this project [here](http://www.codeandramblings.com/index.php/2017/11/08/using-python-and…se-server-update/) and the update, where I add authentication and cross-language serialization [here](http://www.codeandramblings.com/index.php/2017/11/08/using-python-and-twisted-to-write-a-simple-sqlite-database-server-update/)