import logging
import json
import requests
import re

from . import config
from . import hawk


class TokenAuth(requests.auth.AuthBase):

    def __init__(self, token):
        if token.find(':') < 0:
            raise Exception('Invalid token specified', 500)

        self.token = token.split(':')
        self.hawk = hawk.HawkAuthScheme(
            self.token,
            algorithm=config.Config.get('flexapi_client.hawk_algorithm'),
        )

    def __call__(self, req):
        self._set_auth_header(req)
        return req

    def _set_auth_header(self, req):
        req.headers['Authorization'] = self.hawk.get_request_header(req)

    # used after 30x redirects to update auth header for the followup request
    def handle_redirect(self, req, res):
        self.validate_response(res)
        self._set_auth_header(req)

    def validate_response(self, res):
        self.hawk.validate_response(res)


class FlexAPI(object):

    def __init__(self, server=None, token=None, debug=False):
        self.server = 'https://flexapi.nac.net/v1.0'
        self.response = None
        self.auth = None
        self.debug = debug

        if server:
            self.server = server
        elif config.Config.get('flexapi_client.url'):
            self.server = config.Config.get('flexapi_client.url')

        if token:
            self.set_token(token)
        elif config.Config.get('flexapi_client.token'):
            self.set_token(config.Config.get('flexapi_client.token'))

    def set_token(self, token):
        self.auth = TokenAuth(token)

    @property
    def logger(self):
        logger_name = 'flexapi.client.python'
        attribute = '_logger'
        # lazy create logger
        if not hasattr(self, attribute):
            logger = logging.getLogger(logger_name)
            if self.debug:
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter('%(asctime)s %(levelname)s %(message)s'),
                )
                logger.addHandler(handler)
                logger.setLevel(logging.DEBUG)
            else:
                logger.addHandler(logging.NullHandler())

            setattr(self, attribute, logger)
        return getattr(self, attribute)

    def delete(self, url=None):
        return self.request(
            method='DELETE',
            url=url,
            headers={
                'Accept': 'application/json',
            }
        )

    def get(self, url=None, params=None):
        return self.request(
            method='GET',
            url=url,
            params=params,
            headers={
                'Accept': 'application/json',
            }
        )

    def head(self, url=None, params=None):
        return self.request(
            method='HEAD',
            url=url,
            params=params,
            headers={
                'Accept': 'application/json',
            }
        )

    def options(self, url=None, params=None):
        return self.request(
            method='OPTIONS',
            url=url,
            params=params,
            headers={
                'Accept': 'application/json',
            }
        )

    def patch(self, url=None, params=None, files=None):
        return self.request(
            method='PATCH',
            url=url,
            data=json.dumps(params),
            files=files,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        )

    def post(self, url=None, params=None, files=None):
        return self.request(
            method='POST',
            url=url,
            data=json.dumps(params),
            files=files,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        )

    def put(self, url=None, params=None, files=None):
        return self.request(
            method='PUT',
            url=url,
            data=json.dumps(params),
            files=files,
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
            }
        )

    def request(self, *args, **kwargs):
        """wraps _request to be able to catch all thrown exceptions"""
        self.logger.info('Sending {0} request to {1}.'.format(
            kwargs['method'], self.server + kwargs['url']))
        try:
            return self._request(*args, **kwargs)
        except Exception as e:
            try:
                self.logger.error('Error in {0} request to {1}: "{2}"'.format(
                    kwargs['method'], self.server + kwargs['url'], str(e)))
            finally:
                # ignore any exceptions in logger because we want to
                # rethrow the original exception
                raise

    def _request(self, method=None, url=None, params=None, data=None,
                 headers=None, files=None):
        handler = None
        try:
            # add handler to expose requests log messages on STDERR
            if self.debug:
                logger = logging.getLogger('requests')
                handler = logging.StreamHandler()
                handler.setFormatter(
                    logging.Formatter('%(asctime)s %(levelname)s %(message)s'),
                )
                logger.addHandler(handler)
                logger.setLevel(logging.DEBUG)

            # using a session is required to handle 30x properly and
            # regenerate hawk authentication headers on followup requests
            s = requests.Session()

            # called after 30x is received & before final location is requested
            if self.auth is not None:
                s.rebuild_auth = self.auth.handle_redirect

            # if we're attaching files and using json, pass json body as a
            # separate request part named "json"
            if files and headers.get('Content-Type') == 'application/json':
                files.append(
                    ('json', ('request.json', data, 'application/json')))
                data = None
                del headers['Content-Type']

            if not re.match('https?://', url):
                url = self.server + url

            r = requests.Request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                auth=self.auth,
                files=files,
            ).prepare()

            self.response = s.send(r)

            # if response was an error
            if not 200 <= self.response.status_code < 300:
                if (self.response.headers.get('content-type') ==
                        'application/json'):
                    data = self.response.json()
                    if 'error' in data:
                        raise Exception(
                            data['error'],
                            self.response.status_code,
                        )
                    if 'message' in data:
                        raise Exception(
                            data['message'],
                            self.response.status_code,
                        )

                raise Exception(self.response.text, self.response.status_code)

            # only validate successful responses
            if self.auth is not None:
                self.auth.validate_response(self.response)
        finally:
            # clean up debug handler
            if handler:
                logger.removeHandler(handler)

        if (self.response.headers.get('content-type') == 'application/json'):
            data = self.response.json()
            return data

        return self.response.text

# end of script
