from functools import wraps

from flask import Flask, request, render_template, Response
from flaskext.babel import Babel

DEBUG = True
LANGUAGES = ('en', 'es')

app = Flask(__name__)
babel = Babel(app)

#
# authentication stuff
#

def check_auth(username, password):
    return DEBUG or (username == 'guest' and password == 'thepassword')


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
# the good, meaty url handlers
#

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')


@app.route('/networking')
@requires_auth
def networking():
    return render_template('networking.html')


#
# the "magic" as they call it
#

if __name__ == '__main__':
    app.run(debug=DEBUG, port=8000)
