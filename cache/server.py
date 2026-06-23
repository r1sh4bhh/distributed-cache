import socket
import threading
import time
from typing import Optional
from cache.storage import StorageEngine
from cache.protocol import RESPParser, CommandProcessor
from cache.persistence import PersistenceManager


class CacheServer:
    """TCP server for distributed cache"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, max_memory_mb: int = 100,
                 persistence_enabled: bool = True):
        self.host = host
        self.port = port
        self.running = False
        self.persistence_enabled = persistence_enabled
        
        # Initialize persistence
        self.persistence = None
        if persistence_enabled:
            self.persistence = PersistenceManager(rdb_enabled=True, aof_enabled=True)
        
        # Create storage with persistence
        self.storage = StorageEngine(max_memory_mb=max_memory_mb, persistence=self.persistence)
        
        # Restore from disk if available
        if self.persistence:
            restored = self.persistence.restore()
            if restored:
                self.storage.store = restored
                print(f"[SERVER] Restored {len(restored)} entries from disk")
        
        self.processor = CommandProcessor(self.storage)
        self.server_socket: Optional[socket.socket] = None
        self.client_count = 0
        self.total_requests = 0
        self.last_save_time = time.time()
    
    def start(self):
        """Start the cache server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"[SERVER] Cache server started on {self.host}:{self.port}")
            print(f"[SERVER] Max memory: 100MB")
            print(f"[SERVER] Persistence: {'enabled' if self.persistence_enabled else 'disabled'}")
            print(f"[SERVER] Listening for connections...")
            
            # Start periodic save thread
            if self.persistence_enabled:
                save_thread = threading.Thread(target=self._periodic_save, daemon=True)
                save_thread.start()
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    try:
                        client_socket, address = self.server_socket.accept()
                    except socket.timeout:
                        continue
                    
                    self.client_count += 1
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address, self.client_count),
                        daemon=True
                    )
                    client_thread.start()
                except KeyboardInterrupt:
                    break
        
        except Exception as e:
            print(f"[ERROR] Server error: {e}")
        finally:
            self.stop()
    
    def _handle_client(self, client_socket: socket.socket, address: tuple, client_id: int):
        """Handle individual client connection"""
        print(f"[CLIENT {client_id}] Connected from {address[0]}:{address[1]}")
        
        try:
            while self.running:
                # Receive data
                data = client_socket.recv(4096)
                
                if not data:
                    break
                
                self.total_requests += 1
                
                # Parse command
                command = RESPParser.parse_command(data)
                
                if not command:
                    response = RESPParser.encode_error("Invalid protocol")
                else:
                    # Process command
                    result = self.processor.process(command)
                    
                    # Encode response
                    if isinstance(result, str) and result.startswith("wrong") or result.startswith("unknown"):
                        response = RESPParser.encode_error(result)
                    else:
                        response = RESPParser.encode_response(result)
                
                # Send response
                client_socket.sendall(response)
        
        except Exception as e:
            print(f"[CLIENT {client_id}] Error: {e}")
        finally:
            client_socket.close()
            print(f"[CLIENT {client_id}] Disconnected")
    
    def _periodic_save(self):
        """Periodically save cache to RDB"""
        while self.running:
            time.sleep(5)  # Check every 5 seconds
            
            if self.persistence and self.persistence.should_save_snapshot():
                print("[PERSIST] Saving RDB snapshot...")
                self.persistence.save_snapshot(self.storage.store)
                
                # Rewrite AOF if needed
                if self.persistence.aof and self.persistence.aof.should_rewrite():
                    print("[PERSIST] Rewriting AOF file...")
                    self.persistence.rewrite_aof(self.storage.store)
    
    def stop(self):
        """Stop the server"""
        self.running = False
        
        # Final save before shutdown
        if self.persistence:
            print("[PERSIST] Saving final snapshot...")
            self.persistence.save_snapshot(self.storage.store)
        
        if self.server_socket:
            self.server_socket.close()
        print(f"\n[SERVER] Stopped. Total requests: {self.total_requests}")
    
    def get_stats(self) -> dict:
        """Get server statistics"""
        return {
            "clients": self.client_count,
            "total_requests": self.total_requests,
            "cache_stats": self.storage.info()
        }


def main():
    """Run the cache server"""
    server = CacheServer(host="localhost", port=6379, max_memory_mb=100)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        server.stop()


if __name__ == "__main__":
    main()
