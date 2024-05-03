import asyncio
import logging
import socket
from const import (
    SMHUB_INFO,
    QUERY_PORT,
    ANY_IP,
)


class QueryServer:
    """Server class for network queries seraching Smart Hubs"""

    def __init__(self, lp, lan_mac: str):
        self.loop = lp
        self.lan_mac = lan_mac
        self.logger = logging.getLogger(__name__)
        self._q_running = False

    async def initialize(self):
        """Starting the server"""
        resp_header = "\x00\x00\x00\xf7"
        version_str = SMHUB_INFO.SW_VERSION.replace(".", "")[::-1]
        type_str = SMHUB_INFO.TYPE_CODE
        serial_str = SMHUB_INFO.SERIAL
        empty_str_10 = "0000000000"
        mac_str = ""
        for nmbr in self.lan_mac.split(":"):
            mac_str += chr(int(nmbr, 16))
        self.resp_str = (
            resp_header
            + chr(0)
            + version_str
            + type_str
            + empty_str_10
            + serial_str
            + mac_str
        ).encode("iso8859-1")

    async def run_query_srv(self):
        """Server for handling Smart Hub queries."""
        self._q_running = True
        while self._q_running:
            try:
                self.q_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.q_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)
                self.q_sock.bind((ANY_IP, QUERY_PORT))
                self.q_sock.settimeout(0.00002)
                self.logger.info("Query server running")

                self._q_running = True
                while self._q_running:
                    try:
                        data, addr = self.q_sock.recvfrom(10)
                    except Exception:
                        await asyncio.sleep(0.4)
                    else:
                        self.q_sock.sendto(self.resp_str, addr)
            except Exception as error_msg:
                self.logger.error(
                    f"Error in query server: {error_msg}; will be closed and restarted"
                )
                self.q_sock.close()

    def close_query_srv(self):
        """Closing connection"""
        self._q_running = False
        self.q_sock.close()
