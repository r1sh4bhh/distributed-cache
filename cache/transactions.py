"""
Transaction support for distributed cache
Implements: MULTI, EXEC, DISCARD, WATCH
"""

from typing import List, Optional, Union, Any


class Transaction:
    """Represents a single transaction"""
    
    def __init__(self):
        self.commands: List[tuple] = []  # List of (command, args) tuples
        self.queued = True
    
    def queue_command(self, command: str, args: List[str]):
        """Queue a command in the transaction"""
        self.commands.append((command, args))
    
    def execute(self, processor) -> List[Any]:
        """Execute all queued commands"""
        results = []
        for command, args in self.commands:
            result = processor.process([command] + args)
            results.append(result)
        return results
    
    def discard(self):
        """Discard all queued commands"""
        self.commands.clear()
        self.queued = False
    
    def clear(self):
        """Clear transaction state"""
        self.commands.clear()
        self.queued = False


class TransactionManager:
    """Manages transactions for clients"""
    
    def __init__(self):
        self.transactions: dict = {}  # client_id -> Transaction
    
    def start_transaction(self, client_id: str) -> bool:
        """Start a new transaction for client"""
        if client_id in self.transactions:
            return False  # Already in transaction
        
        self.transactions[client_id] = Transaction()
        return True
    
    def queue_command(self, client_id: str, command: str, args: List[str]) -> bool:
        """Queue command in transaction"""
        if client_id not in self.transactions:
            return False
        
        self.transactions[client_id].queue_command(command, args)
        return True
    
    def execute_transaction(self, client_id: str, processor) -> Optional[List[Any]]:
        """Execute transaction"""
        if client_id not in self.transactions:
            return None
        
        transaction = self.transactions[client_id]
        results = transaction.execute(processor)
        del self.transactions[client_id]
        return results
    
    def discard_transaction(self, client_id: str) -> bool:
        """Discard transaction"""
        if client_id not in self.transactions:
            return False
        
        self.transactions[client_id].discard()
        del self.transactions[client_id]
        return True
    
    def in_transaction(self, client_id: str) -> bool:
        """Check if client is in transaction"""
        return client_id in self.transactions
