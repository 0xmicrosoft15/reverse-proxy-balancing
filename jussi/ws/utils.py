# -*- coding: utf-8 -*-
# pylint: disable=protected-access
import asyncio
import sys

PY_35 = sys.version_info >= (3, 5)
PY_352 = sys.version_info >= (3, 5, 2)

if PY_35:
    from collections.abc import Coroutine

    base = Coroutine
else:
    base = object

try:
    ensure_future = asyncio.ensure_future
except AttributeError:
    # pylint: disable=no-member
    ensure_future = asyncio.async


def create_future(loop):
    try:
        return loop.create_future()
    except AttributeError:
        return asyncio.Future(loop=loop)


class _ContextManager(base):
    __slots__ = ('_coro', '_obj')

    def __init__(self, coro):
        self._coro = coro
        self._obj = None

    def send(self, value):
        return self._coro.send(value)

    def throw(self, typ, val=None, tb=None):
        if val is None:
            return self._coro.throw(typ)
        elif tb is None:
            return self._coro.throw(typ, val)
        return self._coro.throw(typ, val, tb)

    def close(self):
        return self._coro.close()

    @property
    def gi_frame(self):
        return self._coro.gi_frame

    @property
    def gi_running(self):
        return self._coro.gi_running

    @property
    def gi_code(self):
        return self._coro.gi_code

    def __next__(self):
        return self.send(None)

    @asyncio.coroutine
    def __iter__(self):
        resp = yield from self._coro
        return resp

    if PY_35:
        def __await__(self):
            resp = yield from self._coro
            return resp

        @asyncio.coroutine
        def __aenter__(self):
            self._obj = yield from self._coro
            return self._obj

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc, tb):
            self._obj.close()
            self._obj = None


class _SAConnectionContextManager(_ContextManager):
    if PY_35:  # pragma: no branch
        if PY_352:
            def __aiter__(self):
                return self._coro
        else:
            @asyncio.coroutine
            def __aiter__(self):
                result = yield from self._coro
                return result


class _PoolContextManager(_ContextManager):
    if PY_35:
        @asyncio.coroutine
        def __aexit__(self, exc_type, exc, tb):
            self._obj.close()
            yield from self._obj.wait_closed()
            self._obj = None


class _PoolAcquireContextManager(_ContextManager):
    __slots__ = ('_coro', '_conn', '_pool')

    def __init__(self, coro, pool):
        # pylint: disable=super-init-not-called
        self._coro = coro
        self._conn = None
        self._pool = pool

    if PY_35:
        @asyncio.coroutine
        def __aenter__(self):
            self._conn = yield from self._coro
            return self._conn

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc, tb):
            yield from self._pool.release(self._conn)
            self._pool = None
            self._conn = None


class _PoolConnectionContextManager:
    # pylint: disable=too-few-public-methods
    """Context manager.

    This enables the following idiom for acquiring and releasing a
    connection around a block:

        with (yield from pool) as conn:
            await conn.send()
            result = await conn.recv()

    while failing loudly when accidentally using:

        with pool:
            <block>
    """

    __slots__ = ('_pool', '_conn')

    def __init__(self, pool, conn):
        self._pool = pool
        self._conn = conn

    def __enter__(self):
        assert self._conn
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._pool.release(self._conn)
        finally:
            self._pool = None
            self._conn = None

    if PY_35:
        @asyncio.coroutine
        def __aenter__(self):
            assert not self._conn
            self._conn = yield from self._pool.acquire()
            return self._conn

        @asyncio.coroutine
        def __aexit__(self, exc_type, exc_val, exc_tb):
            try:
                yield from self._pool.release(self._conn)
            finally:
                self._pool = None
                self._conn = None


def dump_ws_conn_info(logger, conn):
    try:
        logger.error(f'conn_id:{id(conn)}')
        logger.error(f'conn.state:{conn.state}')
        # conn messages async queue
        logger.error(f'conn.messages:{vars(conn.messages)}')
        logger.error(f'conn.messages.maxsize:{conn.messages.maxsize}')
        logger.error(f'conn.messages.maxsize:{conn.messages.maxsize}')
        logger.error(f'conn.messages._getters:{conn.messages._getters}')
        logger.error(f'conn.messages._getters:{conn.messages._getters}')
        logger.error(
            f'conn.messages._unfinished_tasks:{conn.messages._unfinished_tasks}')
        logger.error(
            f'conn.messages._unfinished_tasks:{conn.messages._unfinished_tasks}')
        # StreamReaderProtocol info
        logger.error(f'conn._stream_reader:{vars(conn._stream_reader)}')
        logger.error(f'vars:{vars(conn)}')
    except Exception as e:
        logger.error(e)


if not PY_35:
    # pylint: disable=ungrouped-imports
    try:
        from asyncio import coroutines

        coroutines._COROUTINE_TYPES += (_ContextManager,)
    except BaseException:
        pass
