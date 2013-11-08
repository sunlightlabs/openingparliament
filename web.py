from functools import wraps
import datetime
import json
import os
import re
import urlparse

from flask import Flask, flash, g, redirect, request, render_template, Response
from flask.ext.babel import Babel
import postmark
import pymongo
import requests

LANGUAGES = ('en', 'es')
EMPTY_BLOCK = """<br><br>"""

POSTMARK_KEY = os.environ.get('POSTMARK_KEY', '')
RECAPTCHA_PUBLIC = os.environ.get('RECAPTCHA_PUBLIC', '')
RECAPTCHA_PRIVATE = os.environ.get('RECAPTCHA_PRIVATE', '')


app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRETKEY', '1234567890')

babel = Babel(app)


class CrappyCache(dict):

    MINUTE = 60
    HOUR = 60 * 60
    DAY = 60 * 60 * 24

    def __init__(self, *args, **kwargs):
        self.expiration = kwargs.pop("expiration", None)
        super(CrappyCache, self).__init__(*args, **kwargs)

    def __setitem__(self, key, value):

        now = datetime.datetime.utcnow()
        super(CrappyCache, self).__setitem__(key, (now, value))

    def __getitem__(self, key):

        if key in self:

            (then, val) = super(CrappyCache, self).__getitem__(key)

            if self.expiration is None:
                return val

            now = datetime.datetime.utcnow()
            delta = now - then

            if delta.seconds < self.expiration:
                return val

            del self[key]

SCARY_CACHE = CrappyCache(expiration=CrappyCache.MINUTE * 5)


#
# authentication stuff
#

def check_auth(username, password):
    return username == 'admin' and password == os.environ.get('ADMIN_PASSWORD', '')


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
# template filters
#

@app.template_filter()
def slugify(value):
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)


#
# request lifecycle
#

@app.before_request
def before_request():
    mongo_uri = os.environ.get('MONGOHQ_URL')
    if mongo_uri:
        conn = pymongo.Connection(mongo_uri)
        g.db = conn[os.environ.get('MONGOHQ_DB')]
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


@app.context_processor
def inject_admin():
    return {'admin': True if request.authorization else False}


#
# the good, meaty url handlers
#

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():

    if request.method == 'POST':

        # verify captcha

        captcha_url = "http://www.google.com/recaptcha/api/verify"

        params = {
            "privatekey": RECAPTCHA_PRIVATE,
            "remoteip": "",
            "challenge": request.form['recaptcha_challenge_field'],
            "response": request.form['recaptcha_response_field'],
        }

        response = requests.post(captcha_url, params=params)

        print response.text

        if not response.text.startswith("true"):
            context = {"form": request.form}
            flash('Sorry, your captcha was incorrect. Please try again.')
            return render_template('contact.html', **context)

        # send email

        msg = "%s <%s>\n" % (request.form['name'], request.form['email'])
        if request.form['organization']:
            msg += "%s\n" % request.form['organization']
        msg += "\n%s\n" % request.form['message']

        kwargs = {
            'api_key': POSTMARK_KEY,
            'sender': 'contact@sunlightfoundation.com',
            'reply_to': '%s' % request.form['email'],
            'to': 'johnwonderlich@gmail.com, amandelbaum@ndi.org, dswislow@ndi.org, psecchi@directoriolegislativo.org, melissa@fundar.org.mx, gbrown@sunlightfoundation.com, jkeseru@sunlightfoundation.com',
            'bcc': 'jcarbaugh@sunlightfoundation.com',
            'subject': '[OpeningParliament.org] contact: %s <%s>' % (request.form['name'], request.form['email']),
            'text_body': msg,
        }

        postmark.PMMail(**kwargs).send()

        flash('Your message has been sent. Thank you for contacting us!')
        return redirect('/contact')

    return render_template('contact.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/casestudies')
def casestudies():
    return render_template('casestudies.html')


@app.route('/declaration')
def declaration():
    return render_template('declaration.html')


@app.route('/networking')
def networking():
    return render_template('networking.html')


@app.route('/organizations')
def organizations():
    return render_template('organizations.html')


@app.route('/press')
def press():
    # return render_template('press.html')
    return redirect('/')

@app.route('/export')
def export():
    docs = g.db.blocks.find()
    content = {
        'pages': [{'path': d['path'], 'content': d['content']} for d in docs],
    }
    return Response(json.dumps(content), content_type='application/json')


@app.route('/login')
@requires_auth
def login():
    return redirect('/')


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
# scary RSS proxy method
#

@app.route('/rss')
def rss():

    url = "http://blog.openingparliament.org/rss"

    if url in SCARY_CACHE:
        doc = SCARY_CACHE[url]
    else:
        resp = requests.get(url)
        doc = resp.text
        SCARY_CACHE[url] = doc

    return Response(doc, content_type="text/xml")


#
# the "magic" as they call it
#

if __name__ == '__main__':
    DEBUG = True
    app.run(debug=DEBUG, port=8000)
