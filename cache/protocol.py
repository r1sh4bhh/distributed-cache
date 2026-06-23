"""
Redis Serialization Protocol (RESP) parser
Handles: Simple Strings, Errors, Integers, Bulk Strings, Arrays
"""

from typing import List, Optional, Tuple, Union

class RESPParser:
    """Parse and serialize Redis protocol messages"""
    
    @staticmethod
    def parse_command(data: bytes) -> Optional[List[str]]:
        """
        Parse incoming RESP command
        
        Example input: *2\r\n$3\r\nSET\r\n$5\r\nuser1\r\n
        Returns: ["SET", "user1"]
        """
        if not data:
            return None
        
        try:
            lines = data.decode().split('\r\n')
            
            # First line should be array length: *N
            if not lines[0].startswith('*'):
                return None
            
            num_args = int(lines[0][1:])
            args = []
            idx = 1
            
            for _ in range(num_args):
                # Each arg starts with $N (bulk string length)
                if not lines[idx].startswith('$'):
                    return None
                
                length = int(lines[idx][1:])
                idx += 1
                
                # Next line is the actual string
                arg = lines[idx][:length]
                args.append(arg)
                idx += 1
            
            return args
        except:
            return None
    
    @staticmethod
    def encode_response(response: Union[str, int, bytes, List, None]) -> bytes:
        """
        Encode response to RESP format
        
        Returns:
            - Simple String: +OK\r\n
            - Integer: :100\r\n
            - Bulk String: $6\r\nfoobar\r\n
            - Array: *2\r\n$3\r\nfoo\r\n$3\r\nbar\r\n
            - Null: $-1\r\n
        """
        if response is None:
            return b'$-1\r\n'
        
        if isinstance(response, str):
            # Simple string response (e.g., "OK")
            if response.upper() == "OK":
                return b'+OK\r\n'
            # Bulk string
            return f'${len(response)}\r\n{response}\r\n'.encode()
        
        if isinstance(response, int):
            # Integer response
            return f':{response}\r\n'.encode()
        
        if isinstance(response, bytes):
            # Bulk bytes
            return f'${len(response)}\r\n'.encode() + response + b'\r\n'
        
        if isinstance(response, list):
            # Array
            result = f'*{len(response)}\r\n'.encode()
            for item in response:
                result += RESPParser.encode_response(item)
            return result
        
        if isinstance(response, bool):
            # Boolean as integer (1 or 0)
            return f':{1 if response else 0}\r\n'.encode()
        
        # Default: bulk string of string representation
        s = str(response)
        return f'${len(s)}\r\n{s}\r\n'.encode()
    
    @staticmethod
    def encode_error(message: str) -> bytes:
        """Encode error response"""
        return f'-ERR {message}\r\n'.encode()


class CommandProcessor:
    """Process parsed commands"""
    
    def __init__(self, storage):
        self.storage = storage
        
        # Import managers
        from cache.transactions import TransactionManager
        from cache.bit_operations import BitOperationManager
        from cache.scan import ScanManager
        
        self.transactions = TransactionManager()
        self.bit_ops = BitOperationManager()
        self.scan_manager = ScanManager()
        self.client_id = None  # Set by server per client
    
    def process(self, command: List[str]) -> Union[str, int, bytes, List, None]:
        """
        Process a parsed command
        
        Returns: Response to send to client
        """
        if not command:
            return None
        
        cmd = command[0].upper()
        args = command[1:]
        
        # String commands
        if cmd == "GET":
            return self._get(args)
        elif cmd == "SET":
            return self._set(args)
        elif cmd == "DEL":
            return self._del(args)
        elif cmd == "EXISTS":
            return self._exists(args)
        elif cmd == "EXPIRE":
            return self._expire(args)
        elif cmd == "TTL":
            return self._ttl(args)
        elif cmd == "KEYS":
            return self._keys(args)
        
        # Server commands
        elif cmd == "PING":
            return self._ping(args)
        elif cmd == "ECHO":
            return self._echo(args)
        elif cmd == "INFO":
            return self._info(args)
        elif cmd == "FLUSHALL":
            return self._flushall(args)
        elif cmd == "COMMAND":
            return self._command(args)
        
        # List commands
        elif cmd == "LPUSH":
            return self._lpush(args)
        elif cmd == "RPUSH":
            return self._rpush(args)
        elif cmd == "LPOP":
            return self._lpop(args)
        elif cmd == "RPOP":
            return self._rpop(args)
        elif cmd == "LLEN":
            return self._llen(args)
        elif cmd == "LRANGE":
            return self._lrange(args)
        
        # Hash commands
        elif cmd == "HSET":
            return self._hset(args)
        elif cmd == "HGET":
            return self._hget(args)
        elif cmd == "HMGET":
            return self._hmget(args)
        elif cmd == "HGETALL":
            return self._hgetall(args)
        elif cmd == "HDEL":
            return self._hdel(args)
        elif cmd == "HLEN":
            return self._hlen(args)
        
        # Set commands
        elif cmd == "SADD":
            return self._sadd(args)
        elif cmd == "SREM":
            return self._srem(args)
        elif cmd == "SMEMBERS":
            return self._smembers(args)
        elif cmd == "SCARD":
            return self._scard(args)
        elif cmd == "SISMEMBER":
            return self._sismember(args)
        
        # Transaction commands
        elif cmd == "MULTI":
            return self._multi(args)
        elif cmd == "EXEC":
            return self._exec(args)
        elif cmd == "DISCARD":
            return self._discard(args)
        
        # Bit commands
        elif cmd == "SETBIT":
            return self._setbit(args)
        elif cmd == "GETBIT":
            return self._getbit(args)
        elif cmd == "BITCOUNT":
            return self._bitcount(args)
        elif cmd == "BITOP":
            return self._bitop(args)
        
        # Scan commands
        elif cmd == "SCAN":
            return self._scan(args)
        elif cmd == "HSCAN":
            return self._hscan(args)
        elif cmd == "SSCAN":
            return self._sscan(args)
        
        else:
            return f"unknown command '{cmd}'"
    
    # String operations
    
    def _get(self, args: List[str]) -> Union[str, None]:
        """GET key"""
        if len(args) != 1:
            return "wrong number of arguments for 'get' command"
        
        key = args[0]
        value = self.storage.get(key)
        return value
    
    def _set(self, args: List[str]) -> str:
        """SET key value [EX seconds]"""
        if len(args) < 2:
            return "wrong number of arguments for 'set' command"
        
        key = args[0]
        value = args[1]
        ttl = None
        
        # Parse optional EX parameter
        if len(args) >= 4 and args[2].upper() == "EX":
            try:
                ttl = int(args[3])
            except ValueError:
                return "invalid expire time in 'set' command"
        
        self.storage.set(key, value, ttl)
        return "OK"
    
    def _del(self, args: List[str]) -> int:
        """DEL key [key ...]"""
        if len(args) < 1:
            return "wrong number of arguments for 'del' command"
        
        count = 0
        for key in args:
            if self.storage.delete(key):
                count += 1
        return count
    
    def _exists(self, args: List[str]) -> int:
        """EXISTS key [key ...]"""
        if len(args) < 1:
            return "wrong number of arguments for 'exists' command"
        
        count = 0
        for key in args:
            if self.storage.exists(key):
                count += 1
        return count
    
    def _expire(self, args: List[str]) -> int:
        """EXPIRE key seconds"""
        if len(args) != 2:
            return "wrong number of arguments for 'expire' command"
        
        key = args[0]
        try:
            seconds = int(args[1])
        except ValueError:
            return "value is not an integer or out of range"
        
        return 1 if self.storage.expire(key, seconds) else 0
    
    def _ttl(self, args: List[str]) -> int:
        """TTL key"""
        if len(args) != 1:
            return "wrong number of arguments for 'ttl' command"
        
        key = args[0]
        return self.storage.ttl(key)
    
    def _keys(self, args: List[str]) -> list:
        """KEYS pattern"""
        if len(args) != 1:
            return "wrong number of arguments for 'keys' command"
        
        pattern = args[0]
        return self.storage.keys(pattern)
    
    # Server operations
    
    def _ping(self, args: List[str]) -> str:
        """PING [message]"""
        if len(args) == 0:
            return "PONG"
        return args[0]
    
    def _echo(self, args: List[str]) -> str:
        """ECHO message"""
        if len(args) != 1:
            return "wrong number of arguments for 'echo' command"
        return args[0]
    
    def _info(self, args: List[str]) -> str:
        """INFO"""
        info = self.storage.info()
        result = "# Cache Stats\r\n"
        for key, value in info.items():
            result += f"{key}: {value}\r\n"
        return result
    
    def _flushall(self, args: List[str]) -> str:
        """FLUSHALL"""
        count = self.storage.flush_all()
        return "OK"
    
    def _command(self, args: List[str]) -> list:
        """COMMAND - list available commands"""
        commands = [
            "GET", "SET", "DEL", "EXISTS", "EXPIRE", "TTL", "KEYS",
            "LPUSH", "RPUSH", "LPOP", "RPOP", "LLEN", "LRANGE",
            "HSET", "HGET", "HMGET", "HGETALL", "HDEL", "HLEN",
            "SADD", "SREM", "SMEMBERS", "SCARD", "SISMEMBER",
            "PING", "ECHO", "INFO", "FLUSHALL", "COMMAND"
        ]
        return commands
    
    # List operations
    
    def _lpush(self, args: List[str]) -> Union[str, int]:
        """LPUSH key value [value ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'lpush' command"
        
        key = args[0]
        values = args[1:]
        lst = self.storage.ds_manager.get_list(key)
        return lst.lpush(*values)
    
    def _rpush(self, args: List[str]) -> Union[str, int]:
        """RPUSH key value [value ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'rpush' command"
        
        key = args[0]
        values = args[1:]
        lst = self.storage.ds_manager.get_list(key)
        return lst.rpush(*values)
    
    def _lpop(self, args: List[str]) -> Union[str, None]:
        """LPOP key [count]"""
        if len(args) < 1:
            return "wrong number of arguments for 'lpop' command"
        
        key = args[0]
        count = int(args[1]) if len(args) > 1 else 1
        
        if not self.storage.ds_manager.exists_list(key):
            return None
        
        lst = self.storage.ds_manager.get_list(key)
        return lst.lpop(count)
    
    def _rpop(self, args: List[str]) -> Union[str, None]:
        """RPOP key [count]"""
        if len(args) < 1:
            return "wrong number of arguments for 'rpop' command"
        
        key = args[0]
        count = int(args[1]) if len(args) > 1 else 1
        
        if not self.storage.ds_manager.exists_list(key):
            return None
        
        lst = self.storage.ds_manager.get_list(key)
        return lst.rpop(count)
    
    def _llen(self, args: List[str]) -> int:
        """LLEN key"""
        if len(args) != 1:
            return "wrong number of arguments for 'llen' command"
        
        key = args[0]
        if not self.storage.ds_manager.exists_list(key):
            return 0
        
        lst = self.storage.ds_manager.get_list(key)
        return lst.llen()
    
    def _lrange(self, args: List[str]) -> Union[str, list]:
        """LRANGE key start stop"""
        if len(args) != 3:
            return "wrong number of arguments for 'lrange' command"
        
        key = args[0]
        try:
            start = int(args[1])
            stop = int(args[2])
        except ValueError:
            return "value is not an integer or out of range"
        
        if not self.storage.ds_manager.exists_list(key):
            return []
        
        lst = self.storage.ds_manager.get_list(key)
        return lst.lrange(start, stop)
    
    # Hash operations
    
    def _hset(self, args: List[str]) -> Union[str, int]:
        """HSET key field value [field value ...]"""
        if len(args) < 3 or len(args) % 2 == 0:
            return "wrong number of arguments for 'hset' command"
        
        key = args[0]
        field_values = args[1:]
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        count = 0
        for i in range(0, len(field_values), 2):
            count += hash_obj.hset(field_values[i], field_values[i + 1])
        return count
    
    def _hget(self, args: List[str]) -> Union[str, None]:
        """HGET key field"""
        if len(args) != 2:
            return "wrong number of arguments for 'hget' command"
        
        key = args[0]
        field = args[1]
        
        if not self.storage.ds_manager.exists_hash(key):
            return None
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        return hash_obj.hget(field)
    
    def _hmget(self, args: List[str]) -> Union[str, list]:
        """HMGET key field [field ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'hmget' command"
        
        key = args[0]
        fields = args[1:]
        
        if not self.storage.ds_manager.exists_hash(key):
            return [None] * len(fields)
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        return hash_obj.hmget(*fields)
    
    def _hgetall(self, args: List[str]) -> Union[str, dict]:
        """HGETALL key"""
        if len(args) != 1:
            return "wrong number of arguments for 'hgetall' command"
        
        key = args[0]
        if not self.storage.ds_manager.exists_hash(key):
            return {}
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        return hash_obj.hgetall()
    
    def _hdel(self, args: List[str]) -> Union[str, int]:
        """HDEL key field [field ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'hdel' command"
        
        key = args[0]
        fields = args[1:]
        
        if not self.storage.ds_manager.exists_hash(key):
            return 0
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        return hash_obj.hdel(*fields)
    
    def _hlen(self, args: List[str]) -> Union[str, int]:
        """HLEN key"""
        if len(args) != 1:
            return "wrong number of arguments for 'hlen' command"
        
        key = args[0]
        if not self.storage.ds_manager.exists_hash(key):
            return 0
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        return hash_obj.hlen()
    
    # Set operations
    
    def _sadd(self, args: List[str]) -> Union[str, int]:
        """SADD key member [member ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'sadd' command"
        
        key = args[0]
        members = args[1:]
        
        set_obj = self.storage.ds_manager.get_set(key)
        return set_obj.sadd(*members)
    
    def _srem(self, args: List[str]) -> Union[str, int]:
        """SREM key member [member ...]"""
        if len(args) < 2:
            return "wrong number of arguments for 'srem' command"
        
        key = args[0]
        members = args[1:]
        
        if not self.storage.ds_manager.exists_set(key):
            return 0
        
        set_obj = self.storage.ds_manager.get_set(key)
        return set_obj.srem(*members)
    
    def _smembers(self, args: List[str]) -> Union[str, list]:
        """SMEMBERS key"""
        if len(args) != 1:
            return "wrong number of arguments for 'smembers' command"
        
        key = args[0]
        if not self.storage.ds_manager.exists_set(key):
            return []
        
        set_obj = self.storage.ds_manager.get_set(key)
        return set_obj.smembers()
    
    def _scard(self, args: List[str]) -> Union[str, int]:
        """SCARD key"""
        if len(args) != 1:
            return "wrong number of arguments for 'scard' command"
        
        key = args[0]
        if not self.storage.ds_manager.exists_set(key):
            return 0
        
        set_obj = self.storage.ds_manager.get_set(key)
        return set_obj.scard()
    
    def _sismember(self, args: List[str]) -> Union[str, int]:
        """SISMEMBER key member"""
        if len(args) != 2:
            return "wrong number of arguments for 'sismember' command"
        
        key = args[0]
        member = args[1]
        
        if not self.storage.ds_manager.exists_set(key):
            return 0
        
        set_obj = self.storage.ds_manager.get_set(key)
        return set_obj.sismember(member)
    
    # Transaction operations
    
    def _multi(self, args: List[str]) -> str:
        """MULTI - start transaction"""
        if not self.client_id:
            return "no client context"
        
        if self.transactions.start_transaction(self.client_id):
            return "OK"
        return "ERR already in transaction"
    
    def _exec(self, args: List[str]) -> Union[str, list]:
        """EXEC - execute transaction"""
        if not self.client_id:
            return "no client context"
        
        if not self.transactions.in_transaction(self.client_id):
            return "ERR exec without multi"
        
        results = self.transactions.execute_transaction(self.client_id, self)
        return results if results else []
    
    def _discard(self, args: List[str]) -> str:
        """DISCARD - discard transaction"""
        if not self.client_id:
            return "no client context"
        
        if self.transactions.discard_transaction(self.client_id):
            return "OK"
        return "ERR discard without multi"
    
    # Bit operations
    
    def _setbit(self, args: List[str]) -> Union[str, int]:
        """SETBIT key offset value"""
        if len(args) != 3:
            return "wrong number of arguments for 'setbit' command"
        
        key = args[0]
        try:
            offset = int(args[1])
            value = int(args[2])
        except ValueError:
            return "value is not an integer or out of range"
        
        if value not in [0, 1]:
            return "bit is not an integer or out of range"
        
        from cache.bit_operations import BitField
        current_value = self.storage.get(key) or ""
        bf = BitField(current_value)
        old_bit = bf.setbit(offset, value)
        self.storage.set(key, bf.get_value())
        
        return old_bit
    
    def _getbit(self, args: List[str]) -> Union[str, int]:
        """GETBIT key offset"""
        if len(args) != 2:
            return "wrong number of arguments for 'getbit' command"
        
        key = args[0]
        try:
            offset = int(args[1])
        except ValueError:
            return "value is not an integer or out of range"
        
        from cache.bit_operations import BitField
        current_value = self.storage.get(key) or ""
        bf = BitField(current_value)
        
        return bf.getbit(offset)
    
    def _bitcount(self, args: List[str]) -> Union[str, int]:
        """BITCOUNT key [start end]"""
        if len(args) < 1:
            return "wrong number of arguments for 'bitcount' command"
        
        key = args[0]
        start = None
        end = None
        
        if len(args) >= 3:
            try:
                start = int(args[1])
                end = int(args[2])
            except ValueError:
                return "value is not an integer or out of range"
        
        from cache.bit_operations import BitField
        current_value = self.storage.get(key) or ""
        bf = BitField(current_value)
        
        return bf.bitcount(start, end)
    
    def _bitop(self, args: List[str]) -> Union[str, int]:
        """BITOP operation destkey key [key ...]"""
        if len(args) < 3:
            return "wrong number of arguments for 'bitop' command"
        
        operation = args[0]
        dest_key = args[1]
        src_keys = args[2:]
        
        return self.bit_ops.bitop(operation, dest_key, *src_keys, storage=self.storage)
    
    # Scan operations
    
    def _scan(self, args: List[str]) -> Union[str, list]:
        """SCAN cursor [MATCH pattern] [COUNT count]"""
        if len(args) < 1:
            return "wrong number of arguments for 'scan' command"
        
        try:
            cursor = int(args[0])
        except ValueError:
            return "value is not an integer or out of range"
        
        pattern = "*"
        count = 10
        
        # Parse optional MATCH and COUNT
        i = 1
        while i < len(args):
            if args[i].upper() == "MATCH" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 2
            elif args[i].upper() == "COUNT" and i + 1 < len(args):
                try:
                    count = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        
        next_cursor, items = self.scan_manager.scan_keys(self.storage, cursor, pattern, count)
        return [next_cursor, items]
    
    def _hscan(self, args: List[str]) -> Union[str, list]:
        """HSCAN key cursor [MATCH pattern] [COUNT count]"""
        if len(args) < 2:
            return "wrong number of arguments for 'hscan' command"
        
        key = args[0]
        try:
            cursor = int(args[1])
        except ValueError:
            return "value is not an integer or out of range"
        
        if not self.storage.ds_manager.exists_hash(key):
            return [0, []]
        
        pattern = "*"
        count = 10
        
        # Parse optional MATCH and COUNT
        i = 2
        while i < len(args):
            if args[i].upper() == "MATCH" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 2
            elif args[i].upper() == "COUNT" and i + 1 < len(args):
                try:
                    count = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        
        hash_obj = self.storage.ds_manager.get_hash(key)
        next_cursor, items = self.scan_manager.scan_hash(hash_obj, cursor, pattern, count)
        return [next_cursor, items]
    
    def _sscan(self, args: List[str]) -> Union[str, list]:
        """SSCAN key cursor [MATCH pattern] [COUNT count]"""
        if len(args) < 2:
            return "wrong number of arguments for 'sscan' command"
        
        key = args[0]
        try:
            cursor = int(args[1])
        except ValueError:
            return "value is not an integer or out of range"
        
        if not self.storage.ds_manager.exists_set(key):
            return [0, []]
        
        pattern = "*"
        count = 10
        
        # Parse optional MATCH and COUNT
        i = 2
        while i < len(args):
            if args[i].upper() == "MATCH" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 2
            elif args[i].upper() == "COUNT" and i + 1 < len(args):
                try:
                    count = int(args[i + 1])
                except ValueError:
                    pass
                i += 2
            else:
                i += 1
        
        set_obj = self.storage.ds_manager.get_set(key)
        next_cursor, items = self.scan_manager.scan_set(set_obj, cursor, pattern, count)
        return [next_cursor, items]
