"""Reserve loopback ports without inspecting or terminating other applications."""
from __future__ import annotations

from dataclasses import dataclass
import socket

HOST = "127.0.0.1"


def port_number(value: str | int) -> int:
    port = int(value)
    if not 0 <= port <= 65535:
        raise ValueError("A port must be between 0 and 65535; 0 requests an OS-assigned port.")
    return port


@dataclass
class PortReservation:
    socket: socket.socket

    @property
    def port(self) -> int:
        return self.socket.getsockname()[1]

    def close(self):
        self.socket.close()


def reserve_port(preferred: int, *, strict: bool = False) -> PortReservation:
    """Try the preferred port, nearby ports, then an OS-assigned port.

    A successful bind checks wildcard listeners and Windows excluded port ranges,
    and holds the port until the caller is ready to start its server.
    """
    preferred = port_number(preferred)
    candidates = [preferred]
    if preferred and not strict:
        candidates.extend(range(preferred + 1, min(preferred + 100, 65535) + 1))
        candidates.append(0)
    last_error = None
    for candidate in candidates:
        reservation = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            reservation.bind((HOST, candidate))
            return PortReservation(reservation)
        except OSError as exc:
            last_error = exc
            reservation.close()
    raise OSError(f"Cannot reserve loopback port {preferred}: {last_error}")


def port_available(port: int) -> bool:
    try:
        reservation = reserve_port(port, strict=True)
    except OSError:
        return False
    reservation.close()
    return True
