"""
Bit operations for distributed cache
Implements: SETBIT, GETBIT, BITCOUNT, BITOP
"""

from typing import Optional, List


class BitField:
    """Manages bit operations on strings"""
    
    def __init__(self, value: str = ""):
        # Convert string to bytes for bit manipulation
        self.bytes_array = bytearray(value.encode() if isinstance(value, str) else value)
    
    def setbit(self, offset: int, value: int) -> int:
        """Set bit at offset to 0 or 1"""
        if value not in [0, 1]:
            return -1
        
        # Ensure we have enough bytes
        byte_offset = offset // 8
        bit_offset = 7 - (offset % 8)
        
        while len(self.bytes_array) <= byte_offset:
            self.bytes_array.append(0)
        
        # Get old bit value
        old_bit = (self.bytes_array[byte_offset] >> bit_offset) & 1
        
        # Set new bit value
        if value:
            self.bytes_array[byte_offset] |= (1 << bit_offset)
        else:
            self.bytes_array[byte_offset] &= ~(1 << bit_offset)
        
        return old_bit
    
    def getbit(self, offset: int) -> int:
        """Get bit at offset"""
        byte_offset = offset // 8
        bit_offset = 7 - (offset % 8)
        
        if byte_offset >= len(self.bytes_array):
            return 0
        
        return (self.bytes_array[byte_offset] >> bit_offset) & 1
    
    def bitcount(self, start: Optional[int] = None, end: Optional[int] = None) -> int:
        """Count set bits (1s) in range"""
        if start is None:
            start = 0
        if end is None:
            end = len(self.bytes_array) - 1
        
        # Clamp to valid range
        start = max(0, min(start, len(self.bytes_array) - 1))
        end = max(0, min(end, len(self.bytes_array) - 1))
        
        if start > end:
            return 0
        
        count = 0
        for i in range(start, end + 1):
            byte = self.bytes_array[i]
            # Count set bits in byte
            while byte:
                count += byte & 1
                byte >>= 1
        
        return count
    
    def bitpos(self, bit: int, start: Optional[int] = None, end: Optional[int] = None) -> int:
        """Find first bit set to 0 or 1"""
        if bit not in [0, 1]:
            return -1
        
        if start is None:
            start = 0
        if end is None:
            end = len(self.bytes_array) - 1
        
        start = max(0, min(start, len(self.bytes_array)))
        end = max(0, min(end, len(self.bytes_array)))
        
        for byte_offset in range(start, end + 1):
            if byte_offset >= len(self.bytes_array):
                if bit == 0:
                    return byte_offset * 8
                continue
            
            byte = self.bytes_array[byte_offset]
            for bit_offset in range(8):
                current_bit = (byte >> (7 - bit_offset)) & 1
                if current_bit == bit:
                    return byte_offset * 8 + bit_offset
        
        return -1
    
    def get_value(self) -> str:
        """Get string representation"""
        return self.bytes_array.decode('utf-8', errors='ignore')
    
    def get_bytes(self) -> bytes:
        """Get bytes representation"""
        return bytes(self.bytes_array)


class BitOperationManager:
    """Manages bit operations across strings"""
    
    @staticmethod
    def bitop(operation: str, dest_key: str, *src_keys, storage=None) -> int:
        """
        Perform bitwise operation on multiple strings
        AND, OR, XOR, NOT
        """
        if not src_keys or not storage:
            return 0
        
        # Get all source values
        sources = []
        max_len = 0
        
        for key in src_keys:
            value = storage.get(key)
            if value:
                if isinstance(value, str):
                    bf = BitField(value)
                else:
                    bf = BitField(str(value))
                sources.append(bf)
                max_len = max(max_len, len(bf.bytes_array))
            else:
                sources.append(BitField(""))
        
        # Pad all to same length
        for bf in sources:
            while len(bf.bytes_array) < max_len:
                bf.bytes_array.append(0)
        
        # Perform operation
        result = bytearray(max_len)
        
        if operation.upper() == "AND":
            for i in range(max_len):
                result[i] = sources[0].bytes_array[i]
                for bf in sources[1:]:
                    result[i] &= bf.bytes_array[i]
        
        elif operation.upper() == "OR":
            for i in range(max_len):
                result[i] = 0
                for bf in sources:
                    result[i] |= bf.bytes_array[i]
        
        elif operation.upper() == "XOR":
            for i in range(max_len):
                result[i] = sources[0].bytes_array[i]
                for bf in sources[1:]:
                    result[i] ^= bf.bytes_array[i]
        
        elif operation.upper() == "NOT":
            if len(sources) != 1:
                return 0
            for i in range(max_len):
                result[i] = ~sources[0].bytes_array[i] & 0xFF
        
        else:
            return 0
        
        # Store result
        result_bf = BitField()
        result_bf.bytes_array = result
        storage.set(dest_key, result_bf.get_value())
        
        return len(result)
