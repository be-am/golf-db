db = {
    'user'     : 'admin',
    'password' : '123',
    'host'     : '127.0.0.1',
    'port'     : '3306',
    'database' : 'golf'
}

DB_URL = f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}?charset=utf8"
# DB_URL = f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}"