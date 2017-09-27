# -*- coding: utf-8 -*-

import ujson

import pytest

parse_error = {
    'id': 1,
    'jsonrpc': '2.0',
    'error': {
        'code': -32700,
        'message':
            'Parse error'
    }
}

invalid_request_error = {
    'id': 1,
    'jsonrpc': '2.0',
    'error': {
        'code': -32600,
        'message':
            'Invalid Request',
        'data': {
            'request': None
        }
    }
}

server_error = {
    'id': 1,
    'jsonrpc': '2.0',
    'error': {
        'code': -32000,
        'message':
            'Server error'
    }
}


@pytest.mark.timeout(10)
@pytest.mark.parametrize('jrpc_request, expected', [
    # single jsonrpc steemd request
    (dict(id=1, method='get_block', params=[1000]), invalid_request_error),
])
async def test_validate_jsonrpc_request_middleware(mocked_app_test_cli, jrpc_request, expected):
    mocked_ws_conn, test_cli = mocked_app_test_cli
    mocked_ws_conn.recv.return_value = ujson.dumps(expected)
    response = await test_cli.post('/', json=jrpc_request)

    assert response.status == 200
    assert response.headers['Content-Type'] == 'application/json'
    json_response = await response.json()
    assert 'error_id' in json_response['error']['data']
    del json_response['error']['data']['error_id']
    assert json_response == expected
