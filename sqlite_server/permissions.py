
def setup_key_table(conn):
	curs = conn.cursor()
	try:
		curs.execute("""
			CREATE TABLE IF NOT EXISTS
			REMOTE_ACCESS_KEYS (key varchar)
		""")
	finally:
		curs.close()
		conn.commit()

def lock_key_table(conn):
	curs = conn.cursor()
	try:
		curs.execute("""
			CREATE TRIGGER IF NOT EXISTS update_keys
			BEFORE UPDATE OF key ON REMOTE_ACCESS_KEYS
			BEGIN
				SELECT raise(abort, 'trying to update access key(s)!');
			END;
		""")
		curs.execute("""
			CREATE TRIGGER IF NOT EXISTS insert_keys
			BEFORE INSERT ON REMOTE_ACCESS_KEYS
			BEGIN
				SELECT raise(abort, 'trying to insert access keys(s)!');
			END;
		""")
		curs.execute("""
			CREATE TRIGGER IF NOT EXISTS delete_keys
			BEFORE DELETE ON REMOTE_ACCESS_KEYS
			BEGIN
				SELECT raise(abort, 'trying to delete acccess keys(s)!');
			END;
		""")
	finally:
		curs.close()
		conn.commit()

def unlock_key_table(conn):
	curs = conn.cursor()
	try:
		curs.execute("""
			DROP TRIGGER update_keys;
		""")
		curs.execute("""
			DROP TRIGGER insert_keys;
		""")
		curs.execute("""
			DROP TRIGGER delete_keys;
		""")
	finally:
		curs.close()
		conn.commit()