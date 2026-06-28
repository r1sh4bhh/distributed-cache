# Lazy imports to avoid circular dependencies
# Import only what's needed when importing the package

__all__ = [
    'StorageEngine',
    'CacheEntry',
    'RESPParser',
    'CommandProcessor',
    'CacheServer',
    'RDBPersistence',
    'AOFPersistence',
    'PersistenceManager',
    'CacheList',
    'CacheHash',
    'CacheSet',
    'DataStructureManager',
    'Transaction',
    'TransactionManager',
    'BitField',
    'BitOperationManager',
    'ScanManager',
    'Connection',
    'ConnectionPool',
    'Pipeline',
    'PipelineProcessor',
    'PipelineClient',
    'AsyncRequest',
    'AsyncWorker',
    'AsyncClient'
]

def __getattr__(name):
    """Lazy import on attribute access to avoid circular imports"""
    if name == 'StorageEngine' or name == 'CacheEntry':
        from cache.storage import StorageEngine, CacheEntry
        return StorageEngine if name == 'StorageEngine' else CacheEntry
    elif name == 'RESPParser' or name == 'CommandProcessor':
        from cache.protocol import RESPParser, CommandProcessor
        return RESPParser if name == 'RESPParser' else CommandProcessor
    elif name == 'CacheServer':
        from cache.server import CacheServer
        return CacheServer
    elif name in ('RDBPersistence', 'AOFPersistence', 'PersistenceManager'):
        from cache.persistence import RDBPersistence, AOFPersistence, PersistenceManager
        if name == 'RDBPersistence':
            return RDBPersistence
        elif name == 'AOFPersistence':
            return AOFPersistence
        else:
            return PersistenceManager
    elif name in ('CacheList', 'CacheHash', 'CacheSet', 'DataStructureManager'):
        from cache.data_structures import CacheList, CacheHash, CacheSet, DataStructureManager
        if name == 'CacheList':
            return CacheList
        elif name == 'CacheHash':
            return CacheHash
        elif name == 'CacheSet':
            return CacheSet
        else:
            return DataStructureManager
    elif name in ('Transaction', 'TransactionManager'):
        from cache.transactions import Transaction, TransactionManager
        return Transaction if name == 'Transaction' else TransactionManager
    elif name in ('BitField', 'BitOperationManager'):
        from cache.bit_operations import BitField, BitOperationManager
        return BitField if name == 'BitField' else BitOperationManager
    elif name == 'ScanManager':
        from cache.scan import ScanManager
        return ScanManager
    elif name in ('Connection', 'ConnectionPool'):
        from cache.connection_pool import Connection, ConnectionPool
        return Connection if name == 'Connection' else ConnectionPool
    elif name in ('Pipeline', 'PipelineProcessor', 'PipelineClient'):
        from cache.pipelining import Pipeline, PipelineProcessor, PipelineClient
        if name == 'Pipeline':
            return Pipeline
        elif name == 'PipelineProcessor':
            return PipelineProcessor
        else:
            return PipelineClient
    elif name in ('AsyncRequest', 'AsyncWorker', 'AsyncClient'):
        from cache.async_io import AsyncRequest, AsyncWorker, AsyncClient
        if name == 'AsyncRequest':
            return AsyncRequest
        elif name == 'AsyncWorker':
            return AsyncWorker
        else:
            return AsyncClient
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
