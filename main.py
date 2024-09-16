import os, logging
DEBUG = os.environ.get('DEBUG')
logging.basicConfig(
        format='[%(asctime)s] %(levelname)s %(module)s/%(funcName)s - %(message)s',
        level=logging.DEBUG if DEBUG else logging.INFO)

from flask import abort, Flask, request, redirect, send_file
from flask_cors import CORS
import json
import unicodedata
import re
import hashlib
import glob

import settings

if not settings.SERVER_URL:
    logging.error('Setting SERVER_URL unset, please edit settings.py')
    exit(1)

HOST = '0.0.0.0'

flask_app = Flask(__name__)
CORS(flask_app)

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    return re.sub('[-\s]+', '-', value)

def gen_short_code(title):
    string = title + settings.SECRET_API_KEY
    hash_object = hashlib.sha256(string.encode())
    digest = hash_object.hexdigest()
    return digest[:6]

def check_auth(headers):
    nonce = request.headers.get('x-sharenote-nonce', '')
    key = request.headers.get('x-sharenote-key', '')
    string = nonce + settings.SECRET_API_KEY
    hash_object = hashlib.sha256(string.encode())
    digest = hash_object.hexdigest()
    return digest == key

@flask_app.route('/', methods=['GET'])
def index():
    try:
        return send_file('static/index.html')
    except FileNotFoundError:
        return ''

@flask_app.route('/app.js', methods=['GET'])
def appjs():
    return send_file('assets/app.js')

@flask_app.route('/favicon.ico', methods=['GET'])
def favicon():
    return send_file('assets/favicon.ico')

@flask_app.route('/v1/account/get-key', methods=['GET'])
def get_key():
    return 'Please set your API key in the Share Note plugin settings to the one set in settings.py'

@flask_app.route('/<nid>', methods=['GET'])
def get_note(nid):
    if re.search('[^a-z0-9_-]', nid):
        abort(404)

    note = 'static/' + nid + '.html'

    if os.path.isfile(note):
        return send_file(note)
    else:
        abort(404)

@flask_app.route('/v1/file/check-files', methods=['POST'])
def check_files():
    data = request.get_json()
    files = data['files']
    result = []

    for f in files:
        name = f['hash'] + '.' + f['filetype']
        if os.path.isfile('static/' + name):
            f['url'] = settings.SERVER_URL + '/static/' + name
        else:
            f['url'] = False

        result.append(f)
        logging.debug('File checked: %s', f)

    if os.path.isfile('static/theme.css'):
        # TODO: figure out if css hash is needed and how it matters
        css = dict(url=settings.SERVER_URL + '/static/theme.css')
    else:
        css = False

    return dict(success=True, files=result, css=css)

@flask_app.route('/v1/file/upload', methods=['POST'])
def upload():
    if not check_auth(request.headers):
        abort(401)

    logging.debug('Headers: %s', request.headers)

    name = request.headers['x-sharenote-hash']
    filetype = request.headers['x-sharenote-filetype']

    if re.search(r'[^a-f0-9]', name):
        logging.error('Invalid hash for file name, aborting')
        abort(400)

    if filetype.lower() not in settings.ALLOWED_FILETYPES:
        logging.error('Invalid file type, aborting')
        abort(415)

    # if the file is css, set the file name to user's ID
    if filetype == 'css':
        name = 'theme'

    name += '.' + filetype
    logging.info('Uploaded file: %s', name)

    with open('static/' + name, 'wb') as f:
        f.write(request.data)

    return dict(success=True, url=settings.SERVER_URL + '/static/' + name)

def cook_note(data):
    template = data['template']

    with open('assets/note-template.html', 'r') as f:
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
        settings.SERVER_URL + '/static/theme.css'
    )
    html = html.replace('TEMPLATE_ASSETS_WEBROOT', settings.SERVER_URL)

    # TODO: TEMPLATE_SCRIPTS for mathjax, etc
    html = html.replace('TEMPLATE_SCRIPTS', '')

    # hard code for now:
    html = html.replace('TEMPLATE_BODY', 'class="mod-linux is-frameless is-hidden-frameless obsidian-app theme-light show-inline-title show-ribbon show-view-header is-focused share-note-plugin" style="--zoom-factor: 1; --font-text-size: 16px;"')
    html = html.replace('TEMPLATE_PREVIEW', 'class="markdown-preview-view markdown-rendered node-insert-event allow-fold-headings show-indentation-guide allow-fold-lists show-properties" style="tab-size: 4;"')
    html = html.replace('TEMPLATE_PUSHER', 'class="markdown-preview-pusher" style="width: 1px; height: 0.1px;"')

    html = html.replace('TEMPLATE_NOTE_CONTENT', template['content'])

    # no point, I trust my own server
    html = html.replace('TEMPLATE_ENCRYPTED_DATA', '')

    return html

@flask_app.route('/v1/file/create-note', methods=['POST'])
def create_note():
    if not check_auth(request.headers):
        abort(401)

    data = request.get_json()
    logging.debug('Note data: %s', json.dumps(data, indent=4))
    title = data['template']['title']

    filename = ''

    if 'filename' in data:
        # if a short code gets sent over, try to find the existing note's filename
        # so links don't break in case the note's title changed
        short_code = data['filename']
        search_glob = 'static/*-{}.html'.format(short_code)
        search_result = glob.glob(search_glob)
        if len(search_result) == 1:
            filename = search_result[0]
            if filename.startswith('static/'):
                filename = filename[7:]
            if filename.endswith('.html'):
                filename = filename[:-5]
            logging.info('Using existing filename: %s', filename)

    if not filename:
        short_code = gen_short_code(title)
        slug = slugify(title)
        filename = slug + '-' + short_code
        logging.info('Generating new filename: %s', filename)

    if re.search('[^a-z0-9_-]', filename):
        logging.error('Invalid note name, aborting')
        abort(400)

    html = cook_note(data)

    if title.lower() == 'share note index':
        filename = 'index'

    with open('static/' + filename + '.html', 'w') as f:
        f.write(html)

    return dict(success=True, url=settings.SERVER_URL + '/' + filename)

@flask_app.route('/v1/file/delete', methods=['POST'])
def delete_note():
    if not check_auth(request.headers):
        abort(401)

    data = request.get_json()
    filename = data['filename']

    if filename == 'index':
        search_glob = 'static/index.html'
    else:
        search_glob = 'static/*-{}.html'.format(data['filename'])

    search_result = glob.glob(search_glob)

    if len(search_result) != 1:
        abort(404)

    note = search_result[0]
    os.remove(note)

    return dict(success=True)


if __name__ == '__main__':
    flask_app.run(host=HOST, port=settings.PORT)

