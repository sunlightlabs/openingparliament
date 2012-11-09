from flask import render_template
import codecs
import csv

from web import app


def unicodeit(d):
    for k in list(d.keys()):
        d[k] = d[k] if isinstance(d[k], unicode) else unicode(d[k], 'utf-8')
    return d


with app.test_request_context(''):

    app.preprocess_request()

    with open('data/organizations.csv') as infile:

        orgs = [unicodeit(r) for r in csv.DictReader(infile)]
        orgs = sorted(orgs, cmp=lambda x, y: cmp(x['country'] + x['name'], y['country'] + y['name']))

        countries = sorted(set(o['country'] for o in orgs))

        with codecs.open('templates/_orgs.html', 'w', 'utf-8') as outfile:
            outfile.write(render_template('_orgs-template.html', orgs=orgs, countries=countries))
