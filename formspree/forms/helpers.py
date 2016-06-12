import flask
import werkzeug.datastructures
import urlparse
import requests
import re
import hashlib
import hashids
from urlparse import urljoin

from formspree import settings, log

HASH = lambda x, y: hashlib.md5(x+y+settings.NONCE_SECRET).hexdigest()
EXCLUDE_KEYS = ['_gotcha', '_next', '_subject', '_cc', '_format']
MONTHLY_COUNTER_KEY = 'monthly_{form_id}_{month}'.format
HASHIDS_CODEC = hashids.Hashids(alphabet='abcdefghijklmnopqrstuvwxyz',
                                min_length=8,
                                salt=settings.HASHIDS_SALT)

def ordered_storage(f):
    '''
    By default Flask doesn't maintain order of form arguments, pretty crazy
    From: https://gist.github.com/cbsmith/5069769
    '''

    def decorator(*args, **kwargs):
        flask.request.parameter_storage_class = werkzeug.datastructures.ImmutableOrderedMultiDict
        return f(*args, **kwargs)
    return decorator

def referrer_to_path(r):
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    n = parsed.netloc + parsed.path
    log.debug('Referrer was %s, now %s' % (str(r), n))
    return n

def referrer_to_baseurl(r):
    if not r:
        return ''
    parsed = urlparse.urlparse(r)
    n = parsed.netloc
    log.debug('Referrer was %s, now %s' % (str(r), n))
    return n

def http_form_to_dict(data):
    '''
    Forms are ImmutableMultiDicts,
    convert to json-serializable version
    '''

    ret = {}
    ordered_keys = []

    for elem in data.iteritems(multi=True):
        if not elem[0] in ret.keys():
            ret[elem[0]] = []

            if not elem[0] in EXCLUDE_KEYS:
                ordered_keys.append(elem[0])

        ret[elem[0]].append(elem[1])

    for r in ret.keys():
        ret[r] = ', '.join(ret[r])

    return ret, ordered_keys


def remove_www(host):
    if host.startswith('www.'):
        return host[4:]
    return host


def sitewide_file_check(url, email):
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'http://' + url
    url = urljoin(url, '/formspree-verify.txt')
    log.debug('Checking sitewide file: %s' % url)
    res = requests.get(url, timeout=2)
    if not res.ok:
        log.debug('Nothing found on address.')
        return False

    for line in res.text.splitlines():
        line = line.strip(u'\xef\xbb\xbf ')
        if line == email:
            return True

    log.debug('%s not found in %s' % (email, res.text[:200]))
    return False
