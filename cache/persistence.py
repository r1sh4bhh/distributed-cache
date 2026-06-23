import json
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path


class RDBPersistence:
    """RDB (Redis Database) - Point-in-time snapshots"""
    
    def __init__(self, filepath: str = "cache.rdb"):
        self.filepath = filepath
        self.last_save_time = None
    
    def save(self, store: Dict) -> bool:
        """
        Save entire cache to RDB file
        Format: JSON with timestamp
        """
        try:
            data = {
                "timestamp": time.time(),
                "entries": {}
            }
            
            # Convert entries to serializable format
            for key, entry in store.items():
                data["entries"][key] = {
                    "value": entry.value,
                    "created_at": entry.created_at,
                    "accessed_at": entry.accessed_at,
                    "ttl": entry.ttl
                }
            
            # Write to file atomically
            temp_file = self.filepath + ".tmp"
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Atomic rename
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            os.rename(temp_file, self.filepath)
            
            self.last_save_time = time.time()
            return True
        
        except Exception as e:
            print(f"[RDB] Save failed: {e}")
            return False
    
    def load(self) -> Optional[Dict]:
        """
        Load cache from RDB file
        Returns dict of entries or None if file doesn't exist
        """
        try:
            if not os.path.exists(self.filepath):
                return None
            
            with open(self.filepath, 'r') as f:
                data = json.load(f)
            
            print(f"[RDB] Loaded snapshot from {self.filepath}")
            return data.get("entries", {})
        
        except Exception as e:
            print(f"[RDB] Load failed: {e}")
            return None
    
    def exists(self) -> bool:
        """Check if RDB file exists"""
        return os.path.exists(self.filepath)
    
    def remove(self):
        """Delete RDB file"""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)


class AOFPersistence:
    """AOF (Append-Only File) - Command log for recovery"""
    
    def __init__(self, filepath: str = "cache.aof"):
        self.filepath = filepath
        self.command_count = 0
        self.file_size = 0
        self._ensure_file()
    
    def _ensure_file(self):
        """Create AOF file if doesn't exist"""
        if not os.path.exists(self.filepath):
            open(self.filepath, 'a').close()
    
    def log_command(self, command: str, args: list) -> bool:
        """
        Log command to AOF file
        Format: COMMAND|arg1|arg2|...\n
        """
        try:
            line = f"{command}|" + "|".join(str(arg) for arg in args) + "\n"
            
            with open(self.filepath, 'a') as f:
                f.write(line)
            
            self.command_count += 1
            self.file_size = os.path.getsize(self.filepath)
            return True
        
        except Exception as e:
            print(f"[AOF] Log failed: {e}")
            return False
    
    def replay(self) -> list:
        """
        Replay all commands from AOF file
        Returns list of (command, args) tuples
        """
        commands = []
        
        try:
            if not os.path.exists(self.filepath):
                return commands
            
            with open(self.filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) < 1:
                        continue
                    
                    command = parts[0]
                    args = parts[1:]
                    commands.append((command, args))
            
            print(f"[AOF] Replayed {len(commands)} commands from {self.filepath}")
            return commands
        
        except Exception as e:
            print(f"[AOF] Replay failed: {e}")
            return commands
    
    def rewrite(self, store: Dict) -> bool:
        """
        Rewrite AOF file with current state
        Compacts the file by removing redundant operations
        """
        try:
            # Create new AOF with current state
            temp_file = self.filepath + ".tmp"
            
            with open(temp_file, 'w') as f:
                for key, entry in store.items():
                    # Write SET command with TTL
                    if entry.ttl:
                        ttl = int(entry.ttl - (time.time() - entry.created_at))
                        if ttl > 0:
                            f.write(f"SET|{key}|{entry.value}|{ttl}\n")
                    else:
                        f.write(f"SET|{key}|{entry.value}\n")
            
            # Atomic rename
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            os.rename(temp_file, self.filepath)
            
            self.command_count = len(store)
            self.file_size = os.path.getsize(self.filepath)
            
            print(f"[AOF] Rewritten with {len(store)} entries")
            return True
        
        except Exception as e:
            print(f"[AOF] Rewrite failed: {e}")
            return False
    
    def should_rewrite(self) -> bool:
        """Check if AOF should be rewritten (size-based)"""
        max_size_mb = 10
        return self.file_size > max_size_mb * 1024 * 1024
    
    def remove(self):
        """Delete AOF file"""
        if os.path.exists(self.filepath):
            os.remove(self.filepath)


class PersistenceManager:
    """Manages both RDB and AOF persistence"""
    
    def __init__(self, rdb_enabled: bool = True, aof_enabled: bool = True,
                 rdb_file: str = "cache.rdb", aof_file: str = "cache.aof"):
        self.rdb_enabled = rdb_enabled
        self.aof_enabled = aof_enabled
        self.rdb = RDBPersistence(rdb_file) if rdb_enabled else None
        self.aof = AOFPersistence(aof_file) if aof_enabled else None
        self.last_rdb_save = 0
        self.rdb_save_interval = 60  # Save every 60 seconds
    
    def restore(self) -> Optional[Dict]:
        """
        Restore cache from disk
        Priority: RDB (faster) > AOF (more up-to-date)
        """
        # Try RDB first (faster)
        if self.rdb_enabled and self.rdb.exists():
            entries = self.rdb.load()
            if entries:
                return entries
        
        # Fall back to AOF if available
        if self.aof_enabled:
            entries = {}
            commands = self.aof.replay()
            
            for command, args in commands:
                if command == "SET" and len(args) >= 2:
                    key = args[0]
                    value = args[1]
                    ttl = int(args[2]) if len(args) > 2 else None
                    
                    # Create entry with original timing
                    from cache.storage import CacheEntry
                    entry = CacheEntry(value, ttl)
                    entries[key] = entry
            
            return entries if entries else None
        
        return None
    
    def save_snapshot(self, store: Dict) -> bool:
        """Save RDB snapshot"""
        if not self.rdb_enabled:
            return False
        
        success = self.rdb.save(store)
        if success:
            self.last_rdb_save = time.time()
        return success
    
    def log_command(self, command: str, args: list) -> bool:
        """Log command to AOF"""
        if not self.aof_enabled:
            return False
        
        return self.aof.log_command(command, args)
    
    def should_save_snapshot(self) -> bool:
        """Check if RDB snapshot is needed (time-based)"""
        if not self.rdb_enabled:
            return False
        
        return time.time() - self.last_rdb_save > self.rdb_save_interval
    
    def rewrite_aof(self, store: Dict) -> bool:
        """Compact AOF file"""
        if not self.aof_enabled:
            return False
        
        return self.aof.rewrite(store)
    
    def cleanup(self):
        """Remove persistence files"""
        if self.rdb_enabled:
            self.rdb.remove()
        if self.aof_enabled:
            self.aof.remove()
    
    def get_stats(self) -> dict:
        """Get persistence statistics"""
        stats = {}
        
        if self.rdb_enabled:
            stats["rdb"] = {
                "enabled": True,
                "exists": self.rdb.exists(),
                "last_save": self.last_rdb_save,
                "file_size_mb": os.path.getsize(self.rdb.filepath) / (1024 * 1024) if self.rdb.exists() else 0
            }
        
        if self.aof_enabled:
            stats["aof"] = {
                "enabled": True,
                "command_count": self.aof.command_count,
                "file_size_mb": self.aof.file_size / (1024 * 1024),
                "needs_rewrite": self.aof.should_rewrite()
            }
        
        return stats
