import hashlib
import os
import zipfile
from werkzeug.middleware.proxy_fix import ProxyFix
import tempfile
import requests
import logging
from flask import Flask, render_template, session, request, redirect, url_for
from flask_session import Session
import msal
import app_config
from epub import (_get_css_files, _get_opf_file, _img_inline,
                  _load_css_content, _load_opf_file, _load_page_content,
                  _remove_css_link, container_file, css_inline, get_opf_path,
                  load_opf, mimetype_file)
from onenote import (NoteBook, Section, create_notebook, create_section,
                     create_page, get_page_content)
from utils import load_env_file

app = Flask(__name__)
load_env_file()
app.config.from_object(app_config)
Session(app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# This section is needed for url_for("foo", _external=True) to automatically
# generate http scheme when this sample is running on localhost,
# and to generate https scheme when it is deployed behind reversed proxy.
# See also https://flask.palletsprojects.com/en/1.0.x/deploying/wsgi-standalone/#proxy-setups  # noqa
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)


def _auth_required() -> str:
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    return token["access_token"]


@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    return render_template('index.html',
                           user=session["user"],
                           version=msal.__version__)


@app.route("/login")
def login():
    # Technically we could use empty list [] as scopes to do just sign in,
    # here we choose to also collect end user consent upfront
    session["flow"] = _build_auth_code_flow(scopes=app_config.SCOPE)
    return render_template("login.html",
                           auth_url=session["flow"]["auth_uri"],
                           version=msal.__version__)


# Its absolute URL must match your app's redirect_uri set in AAD
@app.route(app_config.REDIRECT_PATH)
def authorized():
    try:
        cache = _load_cache()
        result = _build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args)
        if "error" in result:
            return render_template("auth_error.html", result=result)
        session["user"] = result.get("id_token_claims")
        _save_cache(cache)
    except ValueError:  # Usually caused by CSRF
        pass  # Simply ignore them
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.clear()  # Wipe out user and its token cache from session
    return redirect(  # Also logout from your tenant's web session
        app_config.AUTHORITY + "/oauth2/v2.0/logout" +
        "?post_logout_redirect_uri=" + url_for("index", _external=True))


@app.route("/graphcall")
def graphcall():
    token = _get_token_from_cache(app_config.SCOPE)
    if not token:
        return redirect(url_for("login"))
    graph_data = requests.get(  # Use token to call downstream service
        f"{app_config.ENDPOINT}/users",
        headers={'Authorization': 'Bearer ' + token['access_token']},
    ).json()
    return render_template('display.html', result=graph_data)


@app.route("/upload")
def graphcall2():
    token = _auth_required()
    return render_template('upload_form.html')


@app.route("/uploader", methods=['POST'])
def uploader():
    token = _auth_required()

    f = request.files['file']
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_file_name = _md5sum(f.filename)
        zip_file_path = os.path.join(temp_dir, zip_file_name)
        f.save(zip_file_path)
        if not zipfile.is_zipfile(zip_file_path):
            print("not a valid zip file")
        with zipfile.ZipFile(zip_file_path) as myzip:
            myzip.extractall(temp_dir)

        container_file_path = os.path.join(temp_dir, container_file)
        opf_file = _get_opf_file(container_file_path)
        opf_file_path = os.path.join(temp_dir, opf_file)
        manifests, page_list = _load_opf_file(opf_file_path)
        code, _book = create_notebook(token, zip_file_name)
        # book = NoteBook(**_book)
        if code != 201:
            return render_template('display.html', result=_book)
        logger.info(f"create notebook {_book['displayName']}")
        code, _section = create_section(token, _book["id"], "epub")
        if code != 201:
            return render_template('display.html', result=_book)
        # section = Section(**_section)
        logger.info(f"create section {_section['displayName']}")
        secton_url = _section["pagesUrl"]
        css_files = _get_css_files(manifests.values())
        css = _load_css_content(temp_dir, css_files)
        for page_ref in page_list[:]:
            page_file = manifests[page_ref].href
            c = _load_page_content(temp_dir, page_file)
            c = _remove_css_link(c)
            c = css_inline(c, css)
            data = dict()
            c, images = _img_inline(temp_dir, c)
            data.update(images)
            data["Presentation"] = ("Presentation", c, 'text/html')
            logger.info(f"create page with {secton_url}")
            p = create_page(token, secton_url, data)
            print(p)
            rc = get_page_content(token, p['contentUrl'])
            # print(rc)
            logger.info(f"create page {p['title']}")
    return render_template('display.html', result=_book)


def _load_cache():
    cache = msal.SerializableTokenCache()
    if session.get("token_cache"):
        cache.deserialize(session["token_cache"])
    return cache


def _save_cache(cache):
    if cache.has_state_changed:
        session["token_cache"] = cache.serialize()


def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        app_config.CLIENT_ID, authority=authority or app_config.AUTHORITY,
        client_credential=app_config.CLIENT_SECRET, token_cache=cache)


def _build_auth_code_flow(authority=None, scopes=None):
    return _build_msal_app(authority=authority).initiate_auth_code_flow(
        scopes or [],
        redirect_uri=url_for("authorized", _external=True))


def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        _save_cache(cache)
        return result


def _md5sum(source: str) -> str:

    r = hashlib.md5(source.encode("utf-8"))
    return r.hexdigest()


app.jinja_env.globals.update(
    _build_auth_code_flow=_build_auth_code_flow)  # Used in template

if __name__ == "__main__":
    app.run()
