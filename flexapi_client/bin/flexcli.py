#!/usr/bin/env python

import argparse
import json
import os
import sys
import mimetypes
import querystring_parser.parser as querystring_parser

from flexapi_client import flexapi


def main(api=None, parser=None, arg_list=None):
    try:
        if parser is None:
            parser = make_parser()

        args = parser.parse_args(arg_list)

        if api is None:
            api = flexapi.FlexAPI(
                server=args.server,
                token=args.token,
                debug=args.debug)

        kwargs = {
            'url': args.url,
        }

        if args.param:
            kwargs['params'] = parse_params(args.param)

        if args.file:
            kwargs['files'] = []
            for f in args.file:
                if '=' not in f:
                    raise Exception((
                        'Invalid file parameter {}'
                        ', should be <key>=<filename>'
                    ).format(f))
                (k, filename) = f.split('=', 1)
                if not os.path.isfile(filename):
                    raise Exception('File {} not found'.format(filename))
                if not os.access(filename, os.R_OK):
                    raise Exception('Cannot read {}'.format(filename))

                kwargs['files'].append((
                    k,
                    (
                        os.path.basename(filename),
                        open(filename, 'rb'),
                        mimetypes.guess_type(filename)[0],
                    ),
                ))

        response = getattr(api, args.method.lower())(**kwargs)

        print json.dumps(response, indent=args.indent,
                         separators=(',', ': '), sort_keys=True)
        return 0
    except KeyboardInterrupt:
        return
    except Exception as e:
        print e
        return 1


def make_parser():
    parser = argparse.ArgumentParser(
        description='Flex API command line client.')
    parser.add_argument('method',
                        choices=['GET', 'POST', 'PATCH',
                                 'PUT', 'HEAD', 'DELETE', 'OPTIONS'],
                        help=u'The request method to use for the api call.')
    parser.add_argument('url', help=u'Api resource endpoint.')
    parser.add_argument('param', nargs='*',
                        help=u'key=value parameters for the API call')
    parser.add_argument('-f', '--file', action='append',
                        help=u'key=filename files to attach to the API call')
    parser.add_argument('-d', '--debug', help=u'Print debug info.',
                        action='store_true')
    parser.add_argument('-i', '--indent', default=4, type=int,
                        help=u'Output indentation level')
    parser.add_argument('-s', '--server', default=None,
                        help=u'Alternate api server/host/port/authority')
    parser.add_argument('-t', '--token', default=None,
                        help=u'Auth token string')
    return parser


def parse_params(params):
    def listify(params):
        if isinstance(params, dict):
            if params.keys() == range(len(params)):
                params = params.values()
            else:
                for k, v in params.iteritems():
                    params[k] = listify(v)
        if isinstance(params, list):
            return [listify(param) for param in params]
        return params

    return listify(querystring_parser.parse('&'.join(params)))


if __name__ == '__main__':
    sys.exit(main())

# end of script
