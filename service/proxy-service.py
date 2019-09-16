from flask import Flask, request, Response, abort, send_file
from functools import wraps
from azure.storage.file import FileService
from azure.storage.blob import BlockBlobService
import logger as logging
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
    PORT = int(os.getenv("PORT", 5000))
    logger = logging.init_logger('azure-storage-service', os.getenv('LOGLEVEL',"INFO"))

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
