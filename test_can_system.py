"""Automated validation suite for the virtual CAN bus and vehicle ECU."""

import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from ecu_simulator import VehicleECU
from virtual_can import CANMessage, VirtualCANBus


@dataclass
class TestResult:
    test_id: str
    test_name: str
    status: str
    details: str


class CANValidationSuite:
    def __init__(self):
        self.results = []

    def run_test(self, test_id, name, test_function):
        try:
            test_function()
            result = TestResult(test_id, name, "PASS", "Requirement verified")
        except AssertionError as error:
            result = TestResult(test_id, name, "FAIL", str(error))
        except Exception as error:
            result = TestResult(
                test_id,
                name,
                "ERROR",
                f"{type(error).__name__}: {error}",
            )

        self.results.append(result)
        print(f"{test_id}: {name:<45} {result.status}")

    @staticmethod
    def create_system():
        bus = VirtualCANBus()
        ecu = VehicleECU(bus)
        received_messages = []
        bus.subscribe(received_messages.append)
        return bus, ecu, received_messages

    def test_standard_can_message(self):
        message = CANMessage(0x123, bytes([0x01, 0x02]), 0.0)
        assert message.arbitration_id == 0x123
        assert message.data == bytes([0x01, 0x02])

    def test_invalid_can_id(self):
        try:
            CANMessage(0x800, bytes([0x00]), 0.0)
        except ValueError:
            return
        raise AssertionError("CAN ID above 0x7FF was accepted")

    def test_oversized_payload(self):
        try:
            CANMessage(0x100, bytes(range(9)), 0.0)
        except ValueError:
            return
        raise AssertionError("Payload longer than 8 bytes was accepted")

    def test_engine_rpm_transmission(self):
        bus, ecu, received = self.create_system()
        ecu.set_engine_rpm(3200)
        ecu.transmit_engine_status()

        assert len(received) == 1
        assert received[0].arbitration_id == VehicleECU.ENGINE_STATUS_ID
        assert VehicleECU.decode_u16(received[0].data) == 3200
        assert len(bus.get_history()) == 1

    def test_vehicle_speed_transmission(self):
        _, ecu, received = self.create_system()
        ecu.set_vehicle_speed(88)
        ecu.transmit_vehicle_speed()

        assert received[0].arbitration_id == VehicleECU.VEHICLE_SPEED_ID
        assert VehicleECU.decode_u16(received[0].data) == 88

    def test_temperature_transmission(self):
        _, ecu, received = self.create_system()
        ecu.set_coolant_temperature(95)
        ecu.transmit_temperature()

        decoded_temperature = received[0].data[0] - 40
        assert decoded_temperature == 95

    def test_invalid_rpm_rejected(self):
        _, ecu, _ = self.create_system()
        try:
            ecu.set_engine_rpm(9000)
        except ValueError:
            return
        raise AssertionError("Invalid engine RPM was accepted")

    def test_overtemperature_dtc(self):
        _, ecu, _ = self.create_system()
        ecu.set_coolant_temperature(120)
        assert "P0217" in ecu.active_dtcs

    def test_normal_temperature_clears_dtc(self):
        _, ecu, _ = self.create_system()
        ecu.set_coolant_temperature(120)
        ecu.set_coolant_temperature(90)
        assert "P0217" not in ecu.active_dtcs

    def test_message_drop_fault(self):
        bus, ecu, received = self.create_system()
        bus.inject_drop_fault(VehicleECU.ENGINE_STATUS_ID)
        result = ecu.transmit_engine_status()

        assert result["status"] == "DROPPED"
        assert len(received) == 0
        assert len(bus.get_history()) == 0

    def test_message_corruption_fault(self):
        bus, ecu, received = self.create_system()
        ecu.set_vehicle_speed(100)

        expected_data = bytes(VehicleECU.encode_u16(100))
        bus.inject_corruption_fault(VehicleECU.VEHICLE_SPEED_ID)
        result = ecu.transmit_vehicle_speed()

        assert result["status"] == "SENT"
        assert len(received) == 1
        assert received[0].data != expected_data

    def test_fault_recovery(self):
        bus, ecu, received = self.create_system()
        bus.inject_drop_fault(VehicleECU.ENGINE_STATUS_ID)
        ecu.transmit_engine_status()

        bus.clear_faults()
        result = ecu.transmit_engine_status()

        assert result["status"] == "SENT"
        assert len(received) == 1

    def execute(self):
        tests = [
            ("CAN-001", "Create valid standard CAN message",
             self.test_standard_can_message),
            ("CAN-002", "Reject invalid CAN arbitration ID",
             self.test_invalid_can_id),
            ("CAN-003", "Reject oversized classic CAN payload",
             self.test_oversized_payload),
            ("ECU-001", "Encode and transmit engine RPM",
             self.test_engine_rpm_transmission),
            ("ECU-002", "Encode and transmit vehicle speed",
             self.test_vehicle_speed_transmission),
            ("ECU-003", "Encode and transmit coolant temperature",
             self.test_temperature_transmission),
            ("ECU-004", "Reject out-of-range engine RPM",
             self.test_invalid_rpm_rejected),
            ("DTC-001", "Set overtemperature diagnostic code",
             self.test_overtemperature_dtc),
            ("DTC-002", "Clear diagnostic code after recovery",
             self.test_normal_temperature_clears_dtc),
            ("FLT-001", "Detect injected CAN message drop",
             self.test_message_drop_fault),
            ("FLT-002", "Detect injected CAN data corruption",
             self.test_message_corruption_fault),
            ("FLT-003", "Recover communication after fault clear",
             self.test_fault_recovery),
        ]

        print("\nVIRTUAL CAN BUS AND ECU VALIDATION")
        print("=" * 70)

        for test_id, name, function in tests:
            self.run_test(test_id, name, function)

        self.save_results()
        self.print_summary()

    def save_results(self):
        with open("can_test_results.csv", "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["test_id", "test_name", "status", "details", "executed_at_utc"]
            )

            timestamp = datetime.now(timezone.utc).isoformat()

            for result in self.results:
                writer.writerow([
                    result.test_id,
                    result.test_name,
                    result.status,
                    result.details,
                    timestamp,
                ])

    def print_summary(self):
        passed = sum(result.status == "PASS" for result in self.results)
        failed = sum(result.status == "FAIL" for result in self.results)
        errors = sum(result.status == "ERROR" for result in self.results)

        print("=" * 70)
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"Total:  {len(self.results)}")
        print("Detailed results saved to can_test_results.csv")

        if failed or errors:
            raise SystemExit(1)


if __name__ == "__main__":
    suite = CANValidationSuite()
    suite.execute()
