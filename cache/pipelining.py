"""
Pipelining for batching multiple commands
Allows sending multiple commands without waiting for responses
"""

from typing import List, Tuple, Any
from cache.protocol import RESPParser


class Pipeline:
    """Pipeline for batching commands"""
    
    def __init__(self):
        self.commands: List[Tuple[str, List[str]]] = []
    
    def add_command(self, command: str, *args) -> 'Pipeline':
        """Add command to pipeline"""
        self.commands.append((command, list(args)))
        return self
    
    def clear(self):
        """Clear pipeline"""
        self.commands.clear()
    
    def get_request(self) -> bytes:
        """Get full RESP request for all commands"""
        if not self.commands:
            return b''
        
        request = b''
        for command, args in self.commands:
            # Build RESP array for this command
            all_args = [command] + args
            cmd_bytes = f"*{len(all_args)}\r\n".encode()
            
            for arg in all_args:
                arg_str = str(arg)
                cmd_bytes += f"${len(arg_str)}\r\n{arg_str}\r\n".encode()
            
            request += cmd_bytes
        
        return request
    
    def size(self) -> int:
        """Get number of commands in pipeline"""
        return len(self.commands)


class PipelineProcessor:
    """Process pipelined responses"""
    
    @staticmethod
    def parse_responses(data: bytes, num_commands: int) -> List[Any]:
        """Parse multiple RESP responses from data"""
        responses = []
        offset = 0
        
        for _ in range(num_commands):
            response, bytes_read = PipelineProcessor._parse_single_response(data[offset:])
            responses.append(response)
            offset += bytes_read
        
        return responses
    
    @staticmethod
    def _parse_single_response(data: bytes) -> Tuple[Any, int]:
        """Parse single RESP response and return (response, bytes_read)"""
        if not data:
            return None, 0
        
        first_byte = chr(data[0])
        
        # Find CRLF
        crlf_pos = data.find(b'\r\n')
        if crlf_pos == -1:
            return None, 0
        
        line = data[1:crlf_pos].decode()
        
        if first_byte == '+':  # Simple string
            return line, crlf_pos + 2
        
        elif first_byte == '-':  # Error
            return f"ERROR: {line}", crlf_pos + 2
        
        elif first_byte == ':':  # Integer
            return int(line), crlf_pos + 2
        
        elif first_byte == '$':  # Bulk string
            length = int(line)
            if length == -1:
                return None, crlf_pos + 2
            
            start = crlf_pos + 2
            end = start + length
            value = data[start:end].decode()
            return value, end + 2
        
        elif first_byte == '*':  # Array
            count = int(line)
            if count == -1:
                return None, crlf_pos + 2
            
            results = []
            offset = crlf_pos + 2
            
            for _ in range(count):
                item, bytes_read = PipelineProcessor._parse_single_response(data[offset:])
                results.append(item)
                offset += bytes_read
            
            return results, offset
        
        return None, crlf_pos + 2


class PipelineClient:
    """Client with pipelining support"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.socket = None
        self.pipeline = Pipeline()
        self.pipelining = False
    
    def connect(self) -> bool:
        """Connect to cache server"""
        try:
            import socket as sock
            self.socket = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
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
    
    def start_pipeline(self):
        """Start pipelining mode"""
        self.pipelining = True
        self.pipeline.clear()
    
    def add_command(self, command: str, *args) -> 'PipelineClient':
        """Add command to pipeline"""
        if self.pipelining:
            self.pipeline.add_command(command, *args)
        return self
    
    def execute_pipeline(self) -> List[Any]:
        """Execute all pipelined commands"""
        if not self.pipelining or self.pipeline.size() == 0:
            return []
        
        # Send all commands at once
        request = self.pipeline.get_request()
        self.socket.sendall(request)
        
        # Receive all responses
        num_commands = self.pipeline.size()
        all_data = b''
        
        # Read enough data for all responses
        while True:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(4096)
                if not data:
                    break
                all_data += data
            except socket.timeout:
                break
        
        # Parse responses
        responses = PipelineProcessor.parse_responses(all_data, num_commands)
        
        # Reset pipeline
        self.pipelining = False
        self.pipeline.clear()
        
        return responses
