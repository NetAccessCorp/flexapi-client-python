import logging
import mohawk

# suppress 'No handlers could be found for logger "mohawk.base"' error
logging.getLogger('mohawk.base').addHandler(logging.NullHandler())


class HawkAuthScheme(object):
    token = None
    algorithm = 'sha256'
    sender = None

    def __init__(self, token, algorithm=None):
        self.token = token
        if algorithm is not None:
            self.algorithm = algorithm

    def validate_response(self, response):
        try:
            self.sender.accept_response(
                response.headers['Server-Authorization'],
                content=response.content,
                content_type=response.headers['Content-Type'])
        except mohawk.exc.HawkFail as e:
            raise Exception('Hawk response validation failed: "{0}"'.format(
                str(e)))

    def get_request_header(self, r):
        # mohawk cannot handle None values so we provide '' instead of None
        content_type = r.headers.get('Content-Type', '')
        # don't sign request body on multipart/form-data requests
        if content_type.startswith('multipart/form-data; boundary='):
            body = ''
        else:
            body = getattr(r, 'body', '')
            if body is None:
                body = ''

        self.sender = mohawk.Sender({
            'id': self.token[0],
            'key': self.token[1],
            'algorithm': self.algorithm},
            url=r.url,
            method=r.method,
            content_type=content_type,
            content=body)

        return self.sender.request_header

# end of script
