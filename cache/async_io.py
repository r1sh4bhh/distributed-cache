"""
Async I/O support for distributed cache
Non-blocking operations using threading and callbacks
"""

import socket
import threading
from typing import Callable, Optional, Any
from queue import Queue
import time


class AsyncRequest:
    """Represents an async request"""
    
    def __init__(self, command: str, args: list, callback: Callable):
        self.command = command
        self.args = args
        self.callback = callback
        self.result = None
        self.error = None
        self.done = False


class AsyncWorker:
    """Worker for processing async requests"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.socket = None
        self.request_queue: Queue = Queue()
        self.running = False
        self.worker_thread = None
    
    def start(self):
        """Start async worker"""
        if self.running:
            return
        
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
    
    def stop(self):
        """Stop async worker"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
    
    def _connect(self):
        """Connect to server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
        except Exception as e:
            print(f"[ASYNC] Connection failed: {e}")
    
    def _worker_loop(self):
        """Main worker loop"""
        self._connect()
        
        while self.running:
            try:
                # Get request with timeout
                request = self.request_queue.get(timeout=1)
                
                # Process request
                self._process_request(request)
            
            except Exception as e:
                # Re-connect on error
                self._connect()
                continue
    
    def _process_request(self, request: AsyncRequest):
        """Process a single async request"""
        try:
            # Build RESP command
            command_parts = [request.command] + request.args
            cmd_bytes = f"*{len(command_parts)}\r\n".encode()
            
            for part in command_parts:
                part_str = str(part)
                cmd_bytes += f"${len(part_str)}\r\n{part_str}\r\n".encode()
            
            # Send request
            self.socket.sendall(cmd_bytes)
            
            # Receive response
            response = self.socket.recv(4096).decode()
            
            # Parse response (simplified)
            if response.startswith('+'):
                request.result = response[1:].split('\r\n')[0]
            elif response.startswith(':'):
                request.result = int(response[1:].split('\r\n')[0])
            elif response.startswith('$'):
                lines = response.split('\r\n')
                length = int(lines[0][1:])
                if length >= 0:
                    request.result = lines[1]
                else:
                    request.result = None
            else:
                request.result = response
            
            request.done = True
            
            # Call callback
            if request.callback:
                request.callback(request.result)
        
        except Exception as e:
            request.error = str(e)
            request.done = True
            if request.callback:
                request.callback(None)
    
    def execute_async(self, command: str, *args, callback: Optional[Callable] = None) -> AsyncRequest:
        """Execute command asynchronously"""
        request = AsyncRequest(command, list(args), callback)
        self.request_queue.put(request)
        return request
    
    def wait_for_result(self, request: AsyncRequest, timeout: float = 5) -> Optional[Any]:
        """Wait for async result"""
        start = time.time()
        while not request.done and time.time() - start < timeout:
            time.sleep(0.01)
        
        if request.done:
            return request.result
        return None


class AsyncClient:
    """Client with async support"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port
        self.worker = AsyncWorker(host, port)
        self.worker.start()
    
    def execute_async(self, command: str, *args, callback: Optional[Callable] = None):
        """Execute command asynchronously"""
        return self.worker.execute_async(command, *args, callback=callback)
    
    def wait_result(self, request: AsyncRequest, timeout: float = 5):
        """Wait for async result"""
        return self.worker.wait_for_result(request, timeout)
    
    def close(self):
        """Close client and worker"""
        self.worker.stop()
