from flask import Flask, request, Response, abort, send_file
from functools import wraps
from azure.storage.file import FileService, SharePermissions
from azure.storage.blob import BlockBlobService, AppendBlobService, BlobPermissions
import logger as logging
import os
import io
import json
from datetime import datetime, timedelta

app = Flask(__name__)

logger = logging.init_logger('azure-storage-service', os.getenv('LOGLEVEL',"INFO"))

DEFAULT_SAS_PARAMS = '{"start_timedelta": null, "expiry_timedelta": "12H"}'

PORT = int(os.getenv("PORT", 5000))
ACCOUNT_NAME = os.getenv("ACCOUNT_NAME")
ACCOUNT_KEY = os.getenv("ACCOUNT_KEY")
SAS_PARAMS = json.loads(os.getenv("SAS_PARAMS",DEFAULT_SAS_PARAMS))

logger.info('starting azure-storage-service with \n\tPORT={}\n\tACCOUNT_NAME={}\n\tLOGLEVEL={}\n\tSAS_PARAMS={}'.format(PORT, ACCOUNT_NAME, os.getenv('LOGLEVEL',"INFO"),SAS_PARAMS))

def get_auth(auth):
    if auth:
        return auth.get('username'), auth.get('password')
    else:
        return ACCOUNT_NAME, ACCOUNT_KEY

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth and not(ACCOUNT_NAME and ACCOUNT_KEY):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


def get_sas_params(args):
    def str_to_timedelta(str):
        days = 0
        hours = 0
        minutes = 0
        if str:
            str = str.upper()
            if str[-1] == 'D':
                days = int(str[:-1])
            elif str[-1] == 'H':
                hours = int(str[:-1])
            elif str[-1] == 'M':
                minutes = int(str[:-1])
        return timedelta(days=days, hours=hours,minutes=minutes)
    start_timedelta_in = args.get('start_timedelta', SAS_PARAMS.get('start_timedelta'))
    expiry_timedelta_in = args.get('expiry_timedelta', SAS_PARAMS.get('expiry_timedelta'))
    start_timedelta_out = str_to_timedelta(start_timedelta_in)
    expiry_timedelta_out = str_to_timedelta(expiry_timedelta_in)
    return start_timedelta_out, expiry_timedelta_out


def get_location(fpath):
    path_list = fpath.split('/')
    directory_name = "/".join(path_list[:-1]) if len(path_list) > 1 else None
    file_name = path_list[-1]
    return directory_name, file_name

@app.route('/file/<share_name>/<path:path_to_file>', methods=['GET'])
@requires_auth
def get_file(share_name, path_to_file):
        try:
            account_name, account_key = get_auth(request.authorization)
            directory_name, file_name = get_location(path_to_file)
            file_service = FileService(account_name = account_name, account_key = account_key)
            f_stream = io.BytesIO()
            file_service.get_file_to_stream(share_name, directory_name, file_name,
            f_stream, max_connections=6)
            f_stream.seek(0)
            return send_file(f_stream, attachment_filename=file_name, as_attachment=True)
        except Exception as e:
            logger.exception(e)
            return abort(500, e)

@app.route('/file/<share_name>/<path:path_to_file>', methods=['POST'])
@requires_auth
def post_file(share_name, path_to_file):
    try:
        account_name, account_key = get_auth(request.authorization)
        file_service = FileService(account_name = account_name, account_key = account_key)
        start_timedelta, expiry_timedelta = get_sas_params(request.args)
        directory_name, file_name = get_location(path_to_file)
        if request.headers.get('Transfer-Encoding') == 'chunked':
            file_service.create_file_from_stream(share_name, directory_name, file_name, request.stream, count=4096)
        else:
            file_service.create_file_from_bytes(share_name, directory_name, file_name, request.get_data())
        sas_token = file_service.generate_file_shared_access_signature(share_name,
            directory_name=directory_name,
            file_name=file_name,
            permission=SharePermissions(read=True),
            expiry=datetime.now() + expiry_timedelta,
            start=start_timedelta,
            id=None,
            ip=None,
            protocol='https',
            cache_control=request.headers.get('Cache-Control'),
            content_disposition=request.headers.get('Content-Disposition: attachment;'),
            content_encoding=request.headers.get('Content-Encoding'),
            content_language=request.headers.get('Content-Language'),
            content_type=request.headers.get('Content-Type'))
        url = file_service.make_file_url(share_name, directory_name, file_name, protocol='https', sas_token=sas_token)

        return Response(response=url+"", status=200, content_type='text/plain')
    except Exception as e:
        logger.exception(e)
        return abort(500, e)

@app.route('/blob/<container_name>/<blob_name>', methods=['POST'])
@requires_auth
def post_blob(container_name, blob_name):
    try:
        account_name, account_key = get_auth(request.authorization)
        file_service = BlockBlobService(account_name = account_name, account_key = account_key)
        start_timedelta, expiry_timedelta = get_sas_params(request.args)

        file_service.create_blob_from_bytes(container_name=container_name, blob_name=blob_name, blob=request.get_data())
        sas_token = file_service.generate_blob_shared_access_signature(container_name=container_name,
            blob_name=blob_name,
            permission=BlobPermissions(read=True),
            expiry=datetime.now() + expiry_timedelta,
            start=start_timedelta,
            id=None,
            ip=None,
            protocol='https',
            cache_control=request.headers.get('Cache-Control'),
            content_disposition=request.headers.get('Content-Disposition: attachment;'),
            content_encoding=request.headers.get('Content-Encoding'),
            content_language=request.headers.get('Content-Language'),
            content_type=request.headers.get('Content-Type'))
        url = file_service.make_blob_url(container_name, blob_name, protocol='https', sas_token=sas_token)

        return Response(response=url+"", status=200, content_type='text/plain')
    except Exception as e:
        logger.exception(e)
        return abort(500, e)
    
@app.route('/appendblob/<container_name>/<blob_name>', methods=['POST'])
@requires_auth
def post_appendblob(container_name, blob_name):
    try:
        account_name, account_key = get_auth(request.authorization)
        file_service = AppendBlobService(account_name = account_name, account_key = account_key)
        start_timedelta, expiry_timedelta = get_sas_params(request.args)

        file_service.create_blob_from_bytes(container_name=container_name, blob_name=blob_name, blob=request.get_data())
        sas_token = file_service.generate_blob_shared_access_signature(container_name=container_name,
            blob_name=blob_name,
            permission=BlobPermissions(read=True),
            expiry=datetime.now() + expiry_timedelta,
            start=start_timedelta,
            id=None,
            ip=None,
            protocol='https',
            cache_control=request.headers.get('Cache-Control'),
            content_disposition=request.headers.get('Content-Disposition: attachment;'),
            content_encoding=request.headers.get('Content-Encoding'),
            content_language=request.headers.get('Content-Language'),
            content_type=request.headers.get('Content-Type'))
        url = file_service.make_blob_url(container_name, blob_name, protocol='https', sas_token=sas_token)

        return Response(response=url+"", status=200, content_type='text/plain')
    except Exception as e:
        logger.exception(e)
        return abort(500, e)

@app.route('/blob/<container_name>/<blob_name>', methods=['GET'])
@requires_auth
def get_blob(container_name, blob_name):
    try:
        account_name, account_key = get_auth(request.authorization)
        blob_service = BlockBlobService(account_name = account_name, account_key = account_key)
        f_stream = io.BytesIO()
        blob_service.get_blob_to_stream(container_name=container_name, blob_name=blob_name,
                                        stream=f_stream, max_connections=6)
        f_stream.seek(0)
        return send_file(f_stream, attachment_filename=blob_name, as_attachment=True)
    except Exception as e:
        logger.exception(e)
        return abort(500, e)

if __name__ == '__main__':
    if os.getenv('WEBFRAMEWORK', '').lower() == 'flask':
        app.run(debug=True, host='0.0.0.0', port=PORT)
    else:
        import cherrypy

        app = logging.add_access_logger(app, logger)
        cherrypy.tree.graft(app, '/')

        # Set the configuration of the web server to production mode
        cherrypy.config.update({
            'environment': 'production',
            'engine.autoreload_on': False,
            'log.screen': True,
            'server.socket_port': PORT,
            'server.socket_host': '0.0.0.0'
        })

        # Start the CherryPy WSGI web server
        cherrypy.engine.start()
        cherrypy.engine.block()
