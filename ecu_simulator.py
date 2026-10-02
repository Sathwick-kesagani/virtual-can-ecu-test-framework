"""Virtual vehicle ECU for CAN communication and diagnostic testing."""

from virtual_can import VirtualCANBus


class VehicleECU:
    ENGINE_STATUS_ID = 0x100
    VEHICLE_SPEED_ID = 0x101
    TEMPERATURE_ID = 0x102
    DIAGNOSTIC_ID = 0x700

    def __init__(self, bus: VirtualCANBus):
        self.bus = bus
        self.engine_rpm = 800
        self.vehicle_speed_kph = 0
        self.coolant_temperature_c = 85
        self.active_dtcs = set()

    @staticmethod
    def encode_u16(value):
        if not 0 <= value <= 65535:
            raise ValueError("16-bit signal must be between 0 and 65535")
        return [(value >> 8) & 0xFF, value & 0xFF]

    @staticmethod
    def decode_u16(data):
        if len(data) < 2:
            raise ValueError("Two bytes are required")
        return (data[0] << 8) | data[1]

    def set_engine_rpm(self, rpm):
        if not 0 <= rpm <= 8000:
            raise ValueError("Engine RPM must be between 0 and 8000")
        self.engine_rpm = rpm

    def set_vehicle_speed(self, speed_kph):
        if not 0 <= speed_kph <= 250:
            raise ValueError("Vehicle speed must be between 0 and 250 km/h")
        self.vehicle_speed_kph = speed_kph

    def set_coolant_temperature(self, temperature_c):
        if not -40 <= temperature_c <= 215:
            raise ValueError("Coolant temperature must be between -40 and 215 C")
        self.coolant_temperature_c = temperature_c

        if temperature_c > 110:
            self.active_dtcs.add("P0217")
        else:
            self.active_dtcs.discard("P0217")

    def transmit_engine_status(self):
        payload = self.encode_u16(self.engine_rpm)
        return self.bus.send(self.ENGINE_STATUS_ID, payload)

    def transmit_vehicle_speed(self):
        payload = self.encode_u16(self.vehicle_speed_kph)
        return self.bus.send(self.VEHICLE_SPEED_ID, payload)

    def transmit_temperature(self):
        encoded_temperature = self.coolant_temperature_c + 40
        return self.bus.send(
            self.TEMPERATURE_ID,
            [encoded_temperature],
        )

    def transmit_all_signals(self):
        return [
            self.transmit_engine_status(),
            self.transmit_vehicle_speed(),
            self.transmit_temperature(),
        ]

    def request_diagnostics(self):
        if not self.active_dtcs:
            payload = [0x00]
        else:
            dtc_count = len(self.active_dtcs)
            payload = [dtc_count]

        return self.bus.send(self.DIAGNOSTIC_ID, payload)

    def clear_diagnostics(self):
        self.active_dtcs.clear()

    def snapshot(self):
        return {
            "engine_rpm": self.engine_rpm,
            "vehicle_speed_kph": self.vehicle_speed_kph,
            "coolant_temperature_c": self.coolant_temperature_c,
            "active_dtcs": sorted(self.active_dtcs),
        }


if __name__ == "__main__":
    can_bus = VirtualCANBus()
    can_bus.subscribe(lambda message: print(message.to_hex()))

    ecu = VehicleECU(can_bus)
    ecu.set_engine_rpm(2500)
    ecu.set_vehicle_speed(65)
    ecu.set_coolant_temperature(95)

    ecu.transmit_all_signals()
    ecu.request_diagnostics()

    print(ecu.snapshot())
