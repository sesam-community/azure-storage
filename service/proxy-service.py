from flask import Flask, request, Response, abort, send_file
from functools import wraps
from azure.storage.file import FileService
from azure.storage.blob import BlockBlobService
import logging
import os
import io

app = Flask(__name__)


def get_var(var):
    envvar = None
    if var.upper() in os.environ:
        envvar = os.environ[var.upper()]
    else:
        envvar = request.args.get(var)
    logger.debug("Setting %s = %s" % (var, envvar))
    return envvar

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
        if not auth:
            return authenticate()
        return f(*args, **kwargs)

    return decorated

@app.route('/file/<share_name>/<directory_name>/<file_name>', methods=['GET'])
@requires_auth
def get_file(share_name, directory_name, file_name):
    auth = request.authorization
    file_service = FileService(account_name = auth.username, account_key = auth.password)
    f_stream = io.BytesIO()
    try:
        file_service.get_file_to_stream(share_name, directory_name, file_name,
                                               f_stream, max_connections=6)
        f_stream.seek(0)
        return send_file(f_stream, attachment_filename=file_name, as_attachment=True)
    except Exception as e:
        return abort(500, e)

@app.route('/blob/<container_name>/<blob_name>', methods=['GET'])
@requires_auth
def get_blob(container_name, blob_name):
    auth = request.authorization
    blob_service = BlockBlobService(account_name = auth.username, account_key = auth.password)
    f_stream = io.BytesIO()
    try:
        blob_service.get_blob_to_stream(container_name=container_name, blob_name=blob_name,
                                        stream=f_stream, max_connections=6)
        f_stream.seek(0)
        return send_file(f_stream, attachment_filename=blob_name, as_attachment=True)
    except Exception as e:
        return abort(500, e)

if __name__ == '__main__':
    # Set up logging
    format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logger = logging.getLogger('http-ftp-proxy-microservice')

    # Log to stdout
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(stdout_handler)

    loglevel = os.environ.get("LOGLEVEL", "INFO")
    if "INFO" == loglevel.upper():
        logger.setLevel(logging.INFO)
    elif "DEBUG" == loglevel.upper():
        logger.setLevel(logging.DEBUG)
    elif "WARN" == loglevel.upper():
        logger.setLevel(logging.WARN)
    elif "ERROR" == loglevel.upper():
        logger.setLevel(logging.ERROR)
    else:
        logger.setlevel(logging.INFO)
        logger.info("Define an unsupported loglevel. Using the default level: INFO.")

    app.run(threaded=True, debug=True, host='0.0.0.0')
