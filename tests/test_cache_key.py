# -*- coding: utf-8 -*-
from collections import OrderedDict

import jussi.cache
import pytest


@pytest.mark.parametrize(
    "jsonrpc_request,expected",
    [
        (OrderedDict([('id', 1), ('jsonrpc', '2.0'), ('method', 'call'),
                      ('params', ['database_api', 'get_account_count', []])]),
         'steemd.database_api.get_account_count'),
        (OrderedDict(
            [('id', 1), ('jsonrpc', '2.0'), ('method', 'call'),
             ('params',
              ['database_api', 'get_account_history', ['steemit', 10, 20]])]),
         "steemd.database_api.get_account_history?params=['steemit',10,20]"),
        (OrderedDict([('id', 1), ('jsonrpc', '2.0'), ('method', 'call'),
                      ('params',
                       ['database_api', 'get_account_references',
                        ['steemit']])]),
         "steemd.database_api.get_account_references?params=['steemit']"),

        # test ordering or dict params
        (OrderedDict([('id', 1), ('jsonrpc', '2.0'),
                      ('method', 'yo.test_dict'), ('params', {
                          'str': '1',
                          'none': None,
                          'dict': {},
                          'int': 1,
                          'list': [],
                      })]),
         "yo.test_dict?params={'dict':{},'int':1,'list':[],'none':None,'str':'1'}"
         ),

        # test list params
        (OrderedDict([('id', 1), ('jsonrpc', '2.0'),
                      ('method', 'sbds.test_list'), ('params', [{}, 1, [], '1',
                                                                None])]),
         "sbds.test_list?params=[{},1,[],'1',None]"),

        # test no params
        (OrderedDict([('id', 1), ('jsonrpc', '2.0'),
                      ('method', 'other.test_no_params')]),
         'other.test_no_params')
    ],
    ids=lambda v: v['method'])
def test_cache_key(jsonrpc_request, expected):
    result = jussi.cache.jsonrpc_cache_key(jsonrpc_request)
    assert result == expected
