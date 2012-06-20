from functools import wraps
import os
import urlparse

from flask import Flask, g, request, render_template, Response
from flaskext.babel import Babel
import pymongo

LANGUAGES = ('en', 'es')
EMPTY_BLOCK = """<br><br>"""

app = Flask(__name__)
babel = Babel(app)


#
# authentication stuff
#

def check_auth(username, password):
    return username == 'guest' and password == 'thepassword'


def authenticate():
    msg = "This site is not yet available to the public. Please login."
    return Response(msg, 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

#
# locale and babel goodness
#

@babel.localeselector
def get_locale():
    if 'lang' in request.args:
        lang = request.args['lang']
        if lang in LANGUAGES:
            return lang
    return request.accept_languages.best_match(LANGUAGES)

#
# request lifecycle
#

@app.before_request
def before_request():
    mongo_uri = os.environ.get('MONGOHQ_URL')
    if mongo_uri:
        conn = pymongo.Connection(mongo_uri)
        db_name = conn.__auth_credentials.keys()[0]
        g.db = conn[db_name]
    else:
        conn = pymongo.Connection()
        g.db = conn['openingparliament']

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.db.connection.disconnect()

@app.context_processor
def inject_content():
    doc = g.db.blocks.find_one({'path': request.path})
    return {'content': doc.get('content') or EMPTY_BLOCK if doc else EMPTY_BLOCK}

#
# the good, meaty url handlers
#

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')


@app.route('/contact')
@requires_auth
def contact():
    return render_template('contact.html')


@app.route('/declaration')
@requires_auth
def declaration():
    return render_template('declaration.html')


@app.route('/networking')
@requires_auth
def networking():
    return render_template('networking.html')

@app.route('/save', methods=['POST'])
@requires_auth
def save():

    content = request.form.get('content', '').strip()
    path = request.form.get('path')
    if not path:
        referrer = request.environ.get('HTTP_REFERER')
        path = urlparse.urlparse(referrer).path

    doc = {
        'path': path,
        'content': content,
    }

    g.db.blocks.update({'path': path}, {"$set": doc}, upsert=True)

    return content


#
# the "magic" as they call it
#

if __name__ == '__main__':
    DEBUG = True
    app.run(debug=DEBUG, port=8000)
