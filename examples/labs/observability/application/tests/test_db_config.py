import unittest,tempfile,sys,json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_config import load_database_url
class DBConfig(unittest.TestCase):
 def test_password_is_not_parsed_as_dsn(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'connection.json';secret='synthetic@:/%"\\ password';p.write_text(json.dumps({'drivername':'postgresql+psycopg','host':'db.example.org','port':5432,'database':'observability','username':'lab_orders','password':secret,'query':{'sslmode':'verify-full','sslrootcert':'/run/db-ca/ca.pem'}}));url=load_database_url(p);self.assertEqual(url.password,secret);self.assertEqual(url.query['sslmode'],'verify-full');self.assertNotIn(secret,str(url))
 def test_plain_postgres_dsn_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'connection';p.write_text('postgresql://user:password@host/db')
   with self.assertRaises(ValueError):load_database_url(p)
 def test_sqlite_native_profile(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'connection';p.write_text('sqlite:////data/lab.db');self.assertEqual(load_database_url(p),'sqlite:////data/lab.db')
if __name__=='__main__':unittest.main()
