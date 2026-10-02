"""Software-only CAN bus simulation for portfolio validation work."""

from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class CANMessage:
    arbitration_id: int
    data: bytes
    timestamp: float

    def __post_init__(self):
        if not 0 <= self.arbitration_id <= 0x7FF:
            raise ValueError("Standard CAN ID must be between 0x000 and 0x7FF")

        if len(self.data) > 8:
            raise ValueError("Classic CAN payload cannot exceed 8 bytes")

        for value in self.data:
            if not 0 <= value <= 255:
                raise ValueError("Each data byte must be between 0 and 255")

    def to_hex(self):
        payload = " ".join(f"{value:02X}" for value in self.data)
        return f"ID=0x{self.arbitration_id:03X} DLC={len(self.data)} DATA=[{payload}]"


class VirtualCANBus:
    """A small in-memory CAN bus with message history and fault injection."""

    def __init__(self):
        self._subscribers = []
        self._history = []
        self._drop_ids = set()
        self._corrupt_ids = set()

    def subscribe(self, callback):
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def send(self, arbitration_id, data):
        message = CANMessage(
            arbitration_id=arbitration_id,
            data=bytes(data),
            timestamp=time(),
        )

        if arbitration_id in self._drop_ids:
            return {
                "status": "DROPPED",
                "message": message,
            }

        if arbitration_id in self._corrupt_ids and message.data:
            corrupted = bytearray(message.data)
            corrupted[0] ^= 0xFF
            message = CANMessage(
                arbitration_id=message.arbitration_id,
                data=bytes(corrupted),
                timestamp=message.timestamp,
            )

        self._history.append(message)

        for callback in list(self._subscribers):
            callback(message)

        return {
            "status": "SENT",
            "message": message,
        }

    def inject_drop_fault(self, arbitration_id):
        self._drop_ids.add(arbitration_id)

    def inject_corruption_fault(self, arbitration_id):
        self._corrupt_ids.add(arbitration_id)

    def clear_faults(self):
        self._drop_ids.clear()
        self._corrupt_ids.clear()

    def get_history(self, arbitration_id=None):
        if arbitration_id is None:
            return list(self._history)

        return [
            message
            for message in self._history
            if message.arbitration_id == arbitration_id
        ]

    def clear_history(self):
        self._history.clear()


if __name__ == "__main__":
    bus = VirtualCANBus()
    bus.subscribe(lambda message: print("RECEIVED:", message.to_hex()))

    bus.send(0x100, [0x01, 0x02, 0x03])
    bus.send(0x200, [0x64, 0x00])

    print(f"Messages stored: {len(bus.get_history())}")
