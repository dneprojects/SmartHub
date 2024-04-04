import logging


class BaseMessage:
    """Base class of SmartIP2 messages."""

    _buffer: bytes = b""
    _length: int = 0
    _crc: int = 0
    _crc_ok = True


class ApiMessage(BaseMessage):
    """Class of messages for the SmartIP2 API."""

    def __init__(self, api_srv, inbuf: bytes, len: int) -> None:
        self.api_srv = api_srv
        self._buffer: bytes = inbuf
        self._rbuffer: bytes = b""
        self._length: int = len
        self.logger = logging.getLogger(__name__)
        self._prefix: str = "\xa8"
        self._postfix: str = "\x3f"
        self._crc = int.from_bytes(inbuf[-3:-1], "big")
        self._crc_ok: bool = self.check_CRC()
        ulen = int(inbuf[3])
        plen = int(inbuf[4 + ulen])
        self._user: str = inbuf[4 : 4 + ulen].decode("iso8859-1")
        self._passw: str = inbuf[5 + ulen : 5 + ulen + plen].decode("iso8859-1")
        self._command: bytes = inbuf[7 + ulen + plen : -3]
        self._cmd_grp: int = self._command[0]
        self._cmd_spec: int = int.from_bytes(self._command[1:3], "big")
        self._cmd_p4: int = self._command[3]
        self._cmd_p5: int = self._command[4]
        self._argi: int = 7 + ulen + plen + 5
        self._dlen: int = int.from_bytes(self._command[5:7], "little")
        self._cmd_data: bytes = self._command[7 : 7 + self._dlen]
        self.response: str = ""
        if not (self._crc_ok):
            self.response = "CRC error"
            self.resp_prepare_std(self.response)

    def check_CRC(self) -> bool:
        """Validates received api message."""
        return calc_crc(self._buffer[:-3]) == self._crc

    def calc_CRC(self, buf) -> tuple[str, str]:
        """Compute CRC for api message."""
        cmd_crc = calc_crc(buf)
        crc_low = cmd_crc & 0xFF
        crc_high = chr((cmd_crc - crc_low) >> 8)
        return chr(crc_low), crc_high

    def get_router_id(self):
        """Pick router id from command"""
        if self._command[3] > 0:
            return self._command[3]
        elif len(self._command) == 7:
            # Test connection
            return 0
        return self._command[7]

    def resp_prepare_std(self, resp):
        """Take response and wrap it into buffer for standard response"""
        self._rbuffer = self._buffer[: self._argi]
        self._dlen = len(resp)
        dlen_low = self._dlen & 0xFF
        dlen_high = (self._dlen - dlen_low) >> 8
        if isinstance(resp, str):
            self._rbuffer += (chr(dlen_low) + chr(dlen_high) + resp).encode("iso8859-1")
        else:
            self._rbuffer = (
                self._rbuffer
                + (chr(dlen_low) + chr(dlen_high)).encode("iso8859-1")
                + resp
            )
        self.resp_prepare_base()

    def resp_prepare_stat(self, rbuffer):
        """Take response and wrap it into buffer for status response"""
        self._rbuffer = self._buffer[: self._argi - 5]
        self._rbuffer += rbuffer[:-3].encode("iso8859-1")  # cut off crc and postfix
        self.resp_prepare_base()

    def resp_prepare_base(self):
        """Basic operations"""
        m_len = len(self._rbuffer) + 3
        mlen_low = m_len & 0xFF
        mlen_high = (m_len - mlen_low) >> 8
        buf_tail = self._rbuffer[3:]
        self._rbuffer = b"\xa8" + (chr(mlen_low) + chr(mlen_high)).encode("iso8859-1")
        self._rbuffer += buf_tail
        crc_low, crc_high = self.calc_CRC(self._rbuffer)
        self._rbuffer += (crc_high + crc_low + self._postfix).encode("iso8859-1")


class RtMessage(BaseMessage):
    """Class of messages for the SmartIP2 API."""

    def __init__(self, api_hdlr, rt_id: int, rt_command: str) -> None:
        self.api_hdlr = api_hdlr
        if api_hdlr.ser_if is not None:
            self.rt_reader = api_hdlr.ser_if[0]
            self.ser_writer = api_hdlr.ser_if[1]
        else:
            self.rt_reader = None
            self.ser_writer = None
        self.logger = logging.getLogger(__name__)
        self.rt = rt_id
        self.rt_command = rt_command
        self._buffer: str = ""
        self._length: int = 0
        self.rt_prepare()
        self._resp_msg = b"\0"
        self._resp_buffer = b"\0\0"
        self._resp_code = 0

    def rt_prepare(self):
        """Set current router, encode, and calc crc"""
        self._buffer = self.rt_command.replace("<rtr>", chr(self.rt))
        cmd_len = chr(len(self._buffer))
        self._buffer = self._buffer[:2] + cmd_len + self._buffer[3:]
        self.calc_CRC()
        self._length = 0
        if len(self._buffer) > 3:
            self._length = ord(self._buffer[2])

    def calc_CRC(self) -> None:
        """Caclulates simple xor checksum"""
        chksum = 0
        self._buffer = self._buffer[:-1]
        for byt in self._buffer:
            chksum ^= ord(byt)
        self._buffer += chr(chksum)

    def check_CRC(self) -> bool:
        """Caclulates simple xor checksum and compares with received value"""
        chksum = 0
        for byt in self._resp_buffer[:-1]:
            chksum ^= byt
        self._crc_ok = self._resp_buffer[-1] == chksum
        return self._crc_ok

    async def rt_send(self) -> None:
        """Sends router command via serial interface"""
        if self.ser_writer is None:
            self.logger.warning("Can't send to router, ser_writer is None")
            return
        self.ser_writer.write(self._buffer.encode("iso8859-1"))
        await self.ser_writer.drain()
        self.logger.debug(f"Sent to router: {self._buffer.encode('iso8859-1')}")

    async def rt_recv(self) -> None:
        """Reads router's response message via serial interface"""
        if self.rt_reader is None:
            self.logger.warning("Can't read from router, rt_reader is None")
            self._resp_code = 0
            self._resp_buffer = b"\0\0"
            self._resp_msg = b"\0\0"
            return
        prefix = await self.rt_reader.readexactly(4)
        if (prefix[3] - 3) < 1:
            self.logger.error("Invalid message length")
            if (b_len := len(self.rt_reader._buffer)) > 0:
                # Empty buffer
                await self.rt_reader.readexactly(b_len)
            raise Exception("Invalid message length")
        tail = await self.rt_reader.readexactly(prefix[3] - 3)
        self._resp_buffer = prefix[1:] + tail
        self._crc = self._resp_buffer[-1]
        self.check_CRC()
        self._resp_code = self._resp_buffer[3]
        self._resp_msg = self._resp_buffer[self._length - 1 : -1]
        if self._resp_code in [250, 251, 253, 254]:
            self.logger.error(
                f"Router returned error {self._resp_code} on command {self.f_hex(self._buffer)}"
            )
        self.logger.debug(f"Router returned: {self._resp_buffer}")

    def f_hex(self, msg: str) -> str:
        """Make pretty hex string."""
        out_msg = ""
        for msg_chr in msg:
            out_msg += f" {ord(msg_chr):02X}"
        return out_msg


class RtResponse(BaseMessage):
    """Class of router response messages."""

    def __init__(self, rt_hdlr, resp_buf) -> None:
        self.hdlr = rt_hdlr
        self.logger = logging.getLogger(__name__)
        self._resp_buffer = resp_buf
        self.rt_parse()

    def __del__(self):
        """Clean up."""
        del self.logger
        del self.hdlr

    def rt_parse(self):
        """Parses incoming response message"""
        self.check_CRC()
        self.resp_cmd = self._resp_buffer[3]
        self.resp_data = self._resp_buffer[4:-1]
        self.resp_dlen = len(self.resp_data)

    def check_CRC(self) -> bool:
        """Caclulates simple xor checksum and compares with received value"""
        chksum = 0
        for byt in self._resp_buffer[:-1]:
            chksum ^= byt
        self._crc_ok = self._resp_buffer[-1] == chksum
        return self._crc_ok


def init_crc16_tbl() -> list[int]:
    """Prepare the crc16 table."""
    res: list[int] = []
    for byte in range(256):
        crc = 0x0000
        for _ in range(8):
            if (byte ^ crc) & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            byte >>= 1
        res.append(crc)
    return res


__crc16_tbl: list[int] = init_crc16_tbl()


def calc_crc(data: bytes) -> int:
    """Calculate a crc16 for the given byte string."""
    crc = 0xFFFF
    for byt in data:
        idx = __crc16_tbl[(crc ^ int(byt)) & 0xFF]
        crc = ((crc >> 8) & 0xFF) ^ idx
    crc_res = ((crc << 8) & 0xFF00) | ((crc >> 8) & 0x00FF)
    return crc_res
