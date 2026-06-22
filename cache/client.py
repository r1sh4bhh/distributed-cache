import socket
from typing import List, Optional, Union
from cache.protocol import RESPParser


class CacheClient:
    """Redis-like client for cache server"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self) -> bool:
        """Connect to cache server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            return True
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        if self.socket:
            self.socket.close()
            self.socket = None
    
    def _send_command(self, *args) -> Union[str, int, list, None]:
        """Send command and receive response"""
        if not self.socket:
            return None
        
        # Build RESP command
        command = f"*{len(args)}\r\n"
        for arg in args:
            arg_str = str(arg)
            command += f"${len(arg_str)}\r\n{arg_str}\r\n"
        
        # Send
        self.socket.sendall(command.encode())
        
        # Receive response
        response = self.socket.recv(4096)
        return self._parse_response(response.decode())
    
    def _parse_response(self, response: str) -> Union[str, int, list, None]:
        """Parse RESP response"""
        if not response:
            return None
        
        first_char = response[0]
        
        if first_char == '+':  # Simple string
            return response[1:].split('\r\n')[0]
        
        elif first_char == '-':  # Error
            return response[1:].split('\r\n')[0]
        
        elif first_char == ':':  # Integer
            return int(response[1:].split('\r\n')[0])
        
        elif first_char == '$':  # Bulk string
            lines = response.split('\r\n')
            length = int(lines[0][1:])
            if length == -1:
                return None
            return lines[1]
        
        elif first_char == '*':  # Array
            lines = response.split('\r\n')
            count = int(lines[0][1:])
            result = []
            idx = 1
            for _ in range(count):
                if lines[idx].startswith('$'):
                    length = int(lines[idx][1:])
                    if length >= 0:
                        result.append(lines[idx + 1])
                    idx += 2
            return result
        
        return response
    
    # String operations
    
    def get(self, key: str) -> Optional[str]:
        """GET key"""
        return self._send_command("GET", key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> str:
        """SET key value [EX seconds]"""
        if ex is not None:
            return self._send_command("SET", key, value, "EX", ex)
        return self._send_command("SET", key, value)
    
    def delete(self, *keys) -> int:
        """DEL key [key ...]"""
        return self._send_command("DEL", *keys)
    
    def exists(self, *keys) -> int:
        """EXISTS key [key ...]"""
        return self._send_command("EXISTS", *keys)
    
    def expire(self, key: str, seconds: int) -> int:
        """EXPIRE key seconds"""
        return self._send_command("EXPIRE", key, seconds)
    
    def ttl(self, key: str) -> int:
        """TTL key"""
        return self._send_command("TTL", key)
    
    def keys(self, pattern: str = "*") -> list:
        """KEYS pattern"""
        return self._send_command("KEYS", pattern)
    
    # Server operations
    
    def ping(self, message: Optional[str] = None) -> str:
        """PING [message]"""
        if message:
            return self._send_command("PING", message)
        return self._send_command("PING")
    
    def echo(self, message: str) -> str:
        """ECHO message"""
        return self._send_command("ECHO", message)
    
    def info(self) -> str:
        """INFO"""
        return self._send_command("INFO")
    
    def flushall(self) -> str:
        """FLUSHALL"""
        return self._send_command("FLUSHALL")
    
    def command(self) -> list:
        """COMMAND"""
        return self._send_command("COMMAND")


def test_basic():
    """Quick test of cache functionality"""
    client = CacheClient()
    
    if not client.connect():
        print("[ERROR] Failed to connect to cache server")
        return
    
    print("[TEST] Connected to cache server")
    
    # Test PING
    result = client.ping()
    print(f"[TEST] PING -> {result}")
    
    # Test SET/GET
    client.set("user:1", "Rishabh")
    result = client.get("user:1")
    print(f"[TEST] SET/GET -> {result}")
    
    # Test EXPIRE
    client.set("temp", "data", ex=2)
    result = client.ttl("temp")
    print(f"[TEST] TTL -> {result}s")
    
    # Test DEL
    result = client.delete("temp")
    print(f"[TEST] DEL -> {result}")
    
    # Test KEYS
    client.set("key1", "val1")
    client.set("key2", "val2")
    result = client.keys()
    print(f"[TEST] KEYS -> {result}")
    
    # Test INFO
    result = client.info()
    print(f"[TEST] INFO:\n{result}")
    
    client.disconnect()
    print("[TEST] Disconnected")


if __name__ == "__main__":
    test_basic()
