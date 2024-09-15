import os, logging
DEBUG = os.environ.get('DEBUG')
logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(module)s/%(funcName)s - %(message)s',
        level=logging.DEBUG if DEBUG else logging.INFO)

from flask import abort, Flask, request, redirect
import json
import unicodedata
import re
import hashlib
from threading import Lock

import secrets

mutex = Lock()

PORT = 8086
HOST = '0.0.0.0' if DEBUG else '127.0.0.1'

flask_app = Flask(__name__, static_url_path='')

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

def gen_short_code(title):
    string = title + secrets.CODE_SEED
    hash_object = hashlib.sha256(string.encode())
    digest = hash_object.hexdigest()
    return digest[:6]

def check_auth(headers):
    nonce = request.headers.get('x-sharenote-nonce', '')
    key = request.headers.get('x-sharenote-key', '')
    string = nonce + secrets.API_KEY
    hash_object = hashlib.sha256(string.encode())
    digest = hash_object.hexdigest()
    return digest == key

@flask_app.route('/', methods=['GET'])
def index():
    return 'Share Note Python API server'

@flask_app.route('/v1/file/check-files', methods=['POST'])
def check_files():
    data = request.get_json()
    files = data['files']
    result = []

    for f in files:
        name = f['hash'] + '.' + f['filetype']
        if os.path.isfile('static/' + name):
            f['url'] = 'https://note-dev.dns.t0.vc/' + name
        else:
            f['url'] = False
        result.append(f)

    print(result)

    return dict(success=True, files=result, css=False)

@flask_app.route('/v1/file/upload', methods=['POST'])
def upload():
    if not check_auth(request.headers):
        abort(401)

    logging.debug('Headers: %s', request.headers)

    name = request.headers['x-sharenote-hash']
    filetype = request.headers['x-sharenote-filetype']

    # if the file is css, set the file name to user's ID
    if request.headers['x-sharenote-filetype'] == 'css':
        name = request.headers['x-sharenote-id']

    name += '.' + filetype

    # TODO: sanitize the name
    with open('static/' + name, 'wb') as f:
        f.write(request.data)

    return dict(url='https://note-dev.dns.t0.vc/' + name)

def cook_note(data, headers):
    template = data['template']

    with open('note-template.html', 'r') as f:
        html = f.read()

    html = html.replace('TEMPLATE_TITLE', template['title'])
    html = html.replace(
        'TEMPLATE_OG_TITLE',
        '<meta property="og:title" content="{}">'.format(template['title'])
    )
    html = html.replace(
        'TEMPLATE_META_DESCRIPTION',
        '<meta name="description" content="{}" property="og:description">'.format(template['description'])
    )
    html = html.replace(   # hard code for now
        'TEMPLATE_WIDTH',
        '.markdown-preview-sizer.markdown-preview-section { max-width: 630px !important; margin: 0 auto; }'
    )
    html = html.replace(
        'TEMPLATE_CSS',
        'https://note-dev.dns.t0.vc/' + request.headers['x-sharenote-id'] + '.css'
    )
    html = html.replace('TEMPLATE_ASSETS_WEBROOT', 'https://note-dev.dns.t0.vc')

    # TODO: TEMPLATE_SCRIPTS for mathjax, etc
    html = html.replace('TEMPLATE_SCRIPTS', '')

    # hard code for now:
    html = html.replace('TEMPLATE_BODY', 'class="mod-linux is-frameless is-hidden-frameless obsidian-app theme-light show-inline-title show-ribbon show-view-header is-focused share-note-plugin" style="--zoom-factor: 1; --font-text-size: 16px;"')
    html = html.replace('TEMPLATE_PREVIEW', 'class="markdown-preview-view markdown-rendered node-insert-event allow-fold-headings show-indentation-guide allow-fold-lists show-properties" style="tab-size: 4;"')
    html = html.replace('TEMPLATE_PUSHER', 'class="markdown-preview-pusher" style="width: 1px; height: 0.1px;"')

    html = html.replace('TEMPLATE_NOTE_CONTENT', template['content'])

    # no point, I trust the server
    html = html.replace('TEMPLATE_ENCRYPTED_DATA', '')

    return html

@flask_app.route('/v1/file/create-note', methods=['POST'])
def create_note():
    if not check_auth(request.headers):
        abort(401)

    data = request.get_json()
    title = data['template']['title']
    short_code = gen_short_code(title)

    logging.debug('Note data: %s', json.dumps(data, indent=4))

    html = cook_note(data, request.headers)
    filename = slugify(title) + '-' + short_code + '.html'

    # TODO: sanitize the name
    with open('static/' + filename, 'w') as f:
        f.write(html)

    return dict(url='https://note-dev.dns.t0.vc/' + filename)


flask_app.run(host=HOST, port=PORT)

