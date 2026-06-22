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
            "PING", "ECHO", "INFO", "FLUSHALL", "COMMAND"
        ]
        return commands
