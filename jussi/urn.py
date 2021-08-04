# -*- coding: utf-8 -*-
import functools
import re
import reprlib
from typing import Dict
from typing import TypeVar
from typing import Union

import structlog
import ujson

from .empty import Empty
from .empty import _empty
from .errors import InvalidNamespaceAPIError
from .errors import InvalidNamespaceError

logger = structlog.get_logger(__name__)

JRPC_METHOD_PATTERN = r'(^(?P<appbase_api>[^\.]+_api)\.(?P<appbase_method>[^\.]+)$)|^(?P<bare_method>^[^\.]+)$|^(?P<namespace>[^\.]+){1}\.(?:(?P<api>[^\.]+)\.){0,1}(?P<method>[^\.]+){1}$'
JRPC_METHOD_REGEX = re.compile(JRPC_METHOD_PATTERN)


STEEMD_NUMERIC_API_MAPPING = ('database_api', 'login_api')


RawRequestDict = Dict[str, Union[str, float, int, list, dict]]
APIType = TypeVar('URNAPIType', Empty, str)
ParamsType = TypeVar('URNParamsType', Empty, list, dict)
ParsedRequestDict = Dict[str, Union[str, float, int, list, dict, Empty]]


FIELD_KEYS = ('namespace', 'api', 'method', 'params')


class URN:
    __slots__ = ('namespace', 'api', 'method', 'params', '__cached_str')

    def __init__(self, namespace: str, api: APIType, method: str, params: ParamsType) -> None:
        self.namespace = namespace
        self.api = api
        self.method = method
        self.params = params
        self.__cached_str = None

    def __repr__(self) -> str:
        return f'URN(namespace={self.namespace}, api={self.api}, method={self.method}, params={reprlib.repr(self.params)})'

    def __str__(self) -> str:
        if self.__cached_str:
            return self.__cached_str
        params = self.params
        if self.params is not _empty:
            params = f'params={ujson.dumps(self.params, ensure_ascii=False)}'

        api = self.api
        if api is not _empty:
            api = str(self.api)
        self.__cached_str = '.'.join(
            p for p in (
                self.namespace,
                api,
                self.method,
                params) if p is not _empty)
        return self.__cached_str

    def to_dict(self) -> dict:
        return {
            'namespace': self.namespace,
            'api': self.api,
            'method': self.method,
            'params': self.params
        }

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, urn) -> bool:
        return hash(urn) == hash(self)


@functools.lru_cache(8192)
def _parse_jrpc_method(jrpc_method: str) -> ParsedRequestDict:
    return JRPC_METHOD_REGEX.match(jrpc_method).groupdict(default=_empty)

# pylint: disable=too-many-branches


def _parse_jrpc(single_jsonrpc_request) -> dict:
    try:
        method = single_jsonrpc_request['method']
        params = single_jsonrpc_request.get('params', _empty)
        #use regex to determine the real namespace, api, method, and params of the request
        matched = _parse_jrpc_method(method)
        if matched.get('appbase_api'): #e.g. condenser_api.method
            return {
                'namespace': 'appbase',
                'api': matched['appbase_api'],
                'method': matched['appbase_method'],
                'params': params
            }
        if matched.get('namespace'): #e.g. steemd.condesner_api.method or jsonrpc.method
            if matched['namespace'] == 'jsonrpc': #if jsonrpc namespace, then use appbase namespace and jsonrpc as api
                return {
                    'namespace': 'appbase',
                    'api': 'jsonrpc',
                    'method': matched['method'],
                    'params': params
                }
            return {
                'namespace': matched['namespace'],
                'api': matched.get('api'),
                'method': matched['method'],
                'params': params
            }
        if matched['bare_method']: #e.g. method
            method = matched['bare_method']

            #if method != call, then it is a steemd.database_api.method call
            if method != 'call':
                return {
                    'namespace': 'steemd',
                    'api': 'database_api',
                    'method': method,
                    'params': params
                }

            #method = call, so params contains info on actual api, method, and parameters
            #probably should be if 2 parameters, then assume no actual parameters
            if len(params) != 3:
                namespace = 'appbase'
                api, method = params
                _params = _empty
            else: #if three parameters
                #remove api and method to get actual parameters
                api, method, _params = params
                #if (api is  condenser_api or jsonrpc) or actual parameters are in a dictionary, then appbase namespace
                if api == 'condenser_api' or isinstance(_params, dict) or api == 'jsonrpc':
                    namespace = 'appbase'
                else:
                    namespace = 'steemd'
            #if api is an integer, map from api integer to api string
            if isinstance(api, int):
                try:
                    api = STEEMD_NUMERIC_API_MAPPING[api]
                except IndexError:
                    raise InvalidNamespaceAPIError(namespace='steemd',
                                                   api=api)

            return {
                'namespace': namespace,
                'api': api,
                'method': method,
                'params': _params
            }
        else:
            raise InvalidNamespaceError(jrpc_request=single_jsonrpc_request,
                                        namespace=single_jsonrpc_request['method'],
                                        matched=matched, params=params)
    except InvalidNamespaceAPIError as e:
        raise e
    except InvalidNamespaceError as e:
        raise e
    except Exception as e:
        raise InvalidNamespaceError(namespace=single_jsonrpc_request['method'],
                                    exception=e)
    # pylint: enable=too-many-branches


def from_request(single_jsonrpc_request: dict) -> URN:
    parsed = _parse_jrpc(single_jsonrpc_request)
    #sort parameters for better caching if a dictionary
    if isinstance(parsed['params'], dict):
        parsed['params'] = dict(sorted(parsed['params'].items()))
    return URN(parsed['namespace'],
               parsed['api'],
               parsed['method'],
               parsed['params'])
