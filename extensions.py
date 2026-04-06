from flask_mysqldb import MySQL
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

mysql   = MySQL()

def init_db(app):
    app.config['MYSQL_SSL_CA'] = 'ca.pem'
    mysql.init_app(app)
limiter = Limiter(key_func=get_remote_address)