import asyncio
from asyncio.streams import StreamReader, StreamWriter
import logging
from logging import Logger, config as log_conf
from logging import RootLogger
from logging.handlers import RotatingFileHandler
import yaml
import serial
import serial.tools.list_ports
import serial_asyncio
import re
import socket
import uuid
import os
import psutil
import cpuinfo
from const import (
    LOGGING_DEF_FILE,
    SMHUB_INFO,
    SMHUB_PORT,
    RT_DEF_ADDR,
    RT_BAUDRATE,
    RT_TIMEOUT,
    RT_CMDS,
)
from api_server import ApiServer, ApiServerMin
from config_server import ConfigServer
from query_server import QueryServer


class SmartHub:
    """Holds methods of Smart Hub."""

    def __init__(self, loop, logger) -> None:
        self.loop = loop
        self.tg = asyncio.TaskGroup()
        self.logger = logger
        self.q_srv: QueryServer
        self.conf_srv: ConfigServer
        self.api_srv: ApiServer
        self._serial: str = ""
        self._pi_model: str = ""
        self._cpu_type: str = ""
        self._cpu_info: dict
        self._host: str = ""
        self._host_ip: str = ""
        self.lan_mac: str = ""
        self.wlan_mac: str = ""
        self.curr_mac: str = ""
        self.info = self.get_info()
        self.get_macs()
        self.logger.info("Smart Hub starting...")
        self.skip_init: bool = False
        self.restart: bool = False

    def reboot_hub(self):
        """Reboot hardware."""
        self.logger.warning("Reboot of Smart Hub host requested")
        os.system("sudo reboot")

    def restart_hub(self, skip_init):
        """Restart SmartHub software."""
        self.skip_init = skip_init > 0
        self.restart = True
        self.logger.warning("Restart of sm_hub process requested")
        self.server.close()
        self.q_srv.close_query_srv()
        for tsk in self.tg._tasks:
            self.logger.info(f"Terminating task {tsk.get_name()}")
            tsk.cancel()

    def get_macs(self):
        """Ask for own mac address."""
        if "eth0" in psutil.net_if_addrs():
            self.lan_mac = psutil.net_if_addrs()["eth0"][-1].address
        else:
            self.lan_mac = psutil.net_if_addrs()["end0"][-1].address
        self.wlan_mac = psutil.net_if_addrs()["wlan0"][-1].address
        self.curr_mac = ":".join(re.findall("..", "%012x" % uuid.getnode()))
        return

    def get_host_ip(self) -> str:
        """Return own ip."""
        return self._host_ip

    def get_version(self) -> str:
        """Return version string"""
        return SMHUB_INFO.SW_VERSION

    def get_serial(self) -> str:
        """Return version string"""
        return SMHUB_INFO.SERIAL

    def get_type(self) -> str:
        """Return version string"""
        return SMHUB_INFO.TYPE

    def get_info(self) -> str:
        """Return information on Smart Hub hardware and software"""  # Get cpu statistics

        if self._serial == "":
            get_all = True
            try:
                with open("/device-tree/model") as f:
                    self._pi_model = f.read()[:-1]
                    f.close()
                with open("/device-tree/serial-number") as f:
                    self._serial = f.read()[:-1]
                    f.close()
                with open("/device-tree/cpus/cpu@0/compatible") as f:
                    self._cpu_type = f.read()[:-1].split(",")[1]
                    f.close()
            except Exception:
                try:
                    with open("/sys/firmware/devicetree/base/model") as f:
                        self._pi_model = f.read()[:-1]
                        f.close()
                    with open("/sys/firmware/devicetree/base/serial-number") as f:
                        self._serial = f.read()[:-1]
                        f.close()
                    with open(
                        "/sys/firmware/devicetree/base/cpus/cpu@0/compatible"
                    ) as f:
                        self._cpu_type = f.read()[:-1].split(",")[1]
                        f.close()
                except Exception:
                    self.logger.info("Using default devicetree")
                    self._pi_model = "Raspberry Pi"
                    self._serial = "10000000e3d90xxx"
                    self._cpu_type = "unknown"
            self._cpu_info = cpuinfo.get_cpu_info()
        else:
            get_all = False

        info_str = "hardware:\n  platform:\n"
        info_str = info_str + "    type: " + self._pi_model + "\n"
        info_str = info_str + "    serial: " + self._serial + "\n"
        info_str = info_str + "  cpu:\n"
        info_str = (
            info_str
            + "    type: "
            + self._cpu_info["arch_string_raw"]
            + " "
            + self._cpu_type
            + "\n"
        )
        info_str = (
            info_str + "    frequency current: " + str(psutil.cpu_freq()[0]) + "MHz\n"
        )
        info_str = (
            info_str + "    frequency max: " + str(psutil.cpu_freq()[-1]) + "MHz\n"
        )
        info_str = info_str + "    load: " + str(psutil.cpu_percent()) + "%\n"
        info_str = (
            info_str
            + "    temperature: "
            + str(round(psutil.sensors_temperatures()["cpu_thermal"][0].current, 1))
            + "°C\n"
        )
        # Calculate memory information
        memory = psutil.virtual_memory()
        info_str = info_str + "  memory:\n"
        info_str = (
            info_str
            + "    free: "
            + str(round(memory.available / 1024.0 / 1024.0, 1))
            + " MB\n"
        )
        info_str = (
            info_str
            + "    total: "
            + str(round(memory.total / 1024.0 / 1024.0, 1))
            + " MB\n"
        )
        info_str = info_str + "    percent: " + str(memory.percent) + "%\n"
        # Calculate disk information
        disk = psutil.disk_usage("/")
        info_str = info_str + "  disk:\n"
        info_str = (
            info_str
            + "    free: "
            + str(round(disk.free / 1024.0 / 1024.0 / 1024.0, 1))
            + " GB\n"
        )
        info_str = (
            info_str
            + "    total: "
            + str(round(disk.total / 1024.0 / 1024.0 / 1024.0, 1))
            + " GB\n"
        )
        info_str = info_str + "    percent: " + str(disk.percent) + "%\n"
        if get_all:
            # Get network info
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self._host_ip = s.getsockname()[0]
            s.close()
            self._host = socket.getfqdn()
        info_str = info_str + "  network:\n"
        info_str = info_str + f"    host: {self._host}\n"
        info_str = info_str + f"    ip: {self._host_ip}\n"
        info_str = info_str + f"    mac: {self.curr_mac}\n"
        info_str = info_str + f"    lan mac: {self.lan_mac}\n"
        info_str = info_str + f"    wlan mac: {self.wlan_mac}\n"

        info_str = info_str + "software:\n"
        info_str = info_str + f"  type: {SMHUB_INFO.TYPE}\n"
        info_str = info_str + f"  version: {SMHUB_INFO.SW_VERSION}\n"

        # Get logging levels
        log_level_cons = self.logger.root.handlers[0].level
        log_level_file = self.logger.root.handlers[1].level
        info_str = info_str + "  loglevel:\n"
        info_str = info_str + f"    console: {log_level_cons}\n"
        info_str = info_str + f"    file: {log_level_file}\n"
        return info_str

    def get_update(self) -> str:
        """Return updated information on Smart Hub sensors and status."""  # Get cpu statistics

        info_str = "hardware:\n"
        info_str = info_str + "  cpu:\n"
        info_str = (
            info_str + "    frequency current: " + str(psutil.cpu_freq()[0]) + "MHz\n"
        )
        info_str = info_str + "    load: " + str(psutil.cpu_percent()) + "%\n"
        info_str = (
            info_str
            + "    temperature: "
            + str(round(psutil.sensors_temperatures()["cpu_thermal"][0].current, 1))
            + "°C\n"
        )
        # Calculate memory information
        memory = psutil.virtual_memory()
        info_str = info_str + "  memory:\n"
        info_str = info_str + "    percent: " + str(memory.percent) + "%\n"
        # Calculate disk information
        disk = psutil.disk_usage("/")
        info_str = info_str + "  disk:\n"
        info_str = info_str + "    percent: " + str(disk.percent) + "%\n"

        info_str = info_str + "software:\n"
        # Get logging levels
        log_level_cons = self.logger.root.handlers[0].level
        log_level_file = self.logger.root.handlers[1].level
        info_str = info_str + "  loglevel:\n"
        info_str = info_str + f"    console: {log_level_cons}\n"
        info_str = info_str + f"    file: {log_level_file}\n"
        return info_str

    async def run_api_server(self, api_srv):
        """Main server for serving Smart Hub calls."""
        self.server = await asyncio.start_server(
            api_srv.handle_api_command, self._host_ip, SMHUB_PORT
        )
        self.logger.info("API server running")
        async with self.server:
            try:
                await self.server.serve_forever()
            except Exception:
                self.logger.warning("Server stopped, restarting Smart Hub ...")
                return self.skip_init


def setup_logging() -> Logger:
    """Initialze logging settings."""

    with open(f"./{LOGGING_DEF_FILE}", "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)
    if logging.root.handlers == []:
        log_conf.dictConfig(config)
    root_logger: RootLogger = logging.root
    root_file_hdlr: RotatingFileHandler = root_logger.handlers[1]  # type: ignore
    root_file_hdlr.doRollover()
    root_logger.propagate = True
    return logging.getLogger(__name__)


async def open_serial_interface(
    device: str, bd_rate: int, logger
) -> tuple[StreamReader, StreamWriter]:
    """Open serial connection of given device."""

    logger.info(f"   Open serial connection: {device}")
    ser_rd, ser_wr = await serial_asyncio.open_serial_connection(
        url=device,
        baudrate=RT_BAUDRATE[bd_rate],
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=RT_TIMEOUT,
        xonxoff=False,
    )

    buf_content = len(ser_rd.__getattribute__("_buffer"))
    if buf_content:
        await ser_rd.readexactly(buf_content)
        logger.info(f"   Emptied serial read buffer of {device}")
    return (ser_rd, ser_wr)


async def init_serial(bd_rate: int, logger):
    """Open and initialize serial interface to router."""

    def prepare_buf_crc(buf: str) -> str:
        """Caclulates simple xor checksum"""
        chksum = 0
        buf = buf[:-1]
        for byt in buf:
            chksum ^= ord(byt)
        buf += chr(chksum)
        return buf

    router_booting = True

    # For Pi5: "dtparam=uart0_console" into config.txt on sd boot partition
    def_device = "/dev/serial0"  # ["/dev/ttyS0", "/dev/ttyS1", "/dev/ttyAMA0", "/dev/tty1", "/dev/tty0"]
    try:
        rt_serial = await open_serial_interface(def_device, bd_rate, logger)
    except Exception as err_msg:
        logger.info(f"   Error opening {def_device}: {err_msg}")

    try:
        new_query = True
        while router_booting:
            if new_query:
                rt_cmd = prepare_buf_crc(
                    RT_CMDS.STOP_MIRROR.replace("<rtr>", chr(RT_DEF_ADDR))
                )
                rt_serial[1].write(rt_cmd.encode("iso8859-1"))
            reading = asyncio.ensure_future(rt_serial[0].read(1024))
            await asyncio.sleep(0.2)
            if reading._state == "FINISHED":
                resp_buf = reading.result()
                if len(resp_buf) < 4:
                    # sometimes just 0xff comes, needs another read
                    logger.debug(f"   Unexpected short test response: {resp_buf}")
                    new_query = False
                elif new_query and (resp_buf[4] == 0x87):
                    logger.info("   Router available")
                    router_booting = False
                elif (not new_query) and (resp_buf[3] == 0x87):
                    logger.info("   Router available")
                    router_booting = False
                elif new_query and (resp_buf[4] == 0xFD):  # 253
                    logger.info("   Waiting for router booting...")
                    await asyncio.sleep(5)
                    new_query = True
                elif (not new_query) and (resp_buf[3] == 0xFD):  # 253
                    logger.info("   Waiting for router booting...")
                    await asyncio.sleep(5)
                    new_query = True
                elif resp_buf[1:-1] == b"#\x01\x06\xc9\xff":
                    logger.info("   Router in ISP mode. Restarting system...")
                    rt_cmd = prepare_buf_crc(
                        RT_CMDS.SYSTEM_RESTART.replace("<rtr>", chr(RT_DEF_ADDR))
                    )
                    rt_serial[1].write(rt_cmd.encode("iso8859-1"))
                else:
                    logger.info("   Retry to connect router")
                    logger.debug(f"   Unexpected test response: {resp_buf}")
                    new_query = True
            else:
                raise Exception("   No test response received")
    except Exception as err_msg:
        logger.error(f"   Error during test stop mirror command: {err_msg}")
        rt_serial = None
    return rt_serial


async def close_serial_interface(rt_serial):
    """Closes connection, uses writer"""
    rt_serial[1].close()
    await rt_serial[1].wait_closed()


async def main(ev_loop):
    """Open serial connection, start server, and tasks"""
    init_flag = True
    startup_ok = False
    retry_max = 3
    retry_serial = retry_max
    logger = setup_logging()
    try:
        # Instantiate SmartHub object
        sm_hub = SmartHub(ev_loop, logger)
        rt_serial = None
        bd_rate = 0
        while (rt_serial is None) and (retry_serial >= 0):
            if retry_serial < retry_max:
                logger.warning(
                    f"   Initialization of serial connection failed, retry {retry_max-retry_serial}"
                )
            rt_serial = await init_serial(bd_rate, logger)  # lower baud rate
            if rt_serial is None:
                bd_rate = 1
                rt_serial = await init_serial(bd_rate, logger)  # higher baud rate
            retry_serial -= 1
        if rt_serial is None:
            init_flag = False
            running_online = False
            logger.error(
                "   Initialization of serial connection failed, running offline"
            )
        else:
            logger.info(
                f"   Initialization of serial connection with {RT_BAUDRATE[bd_rate]} baud succeeded"
            )
            running_online = True
        if running_online:
            # Instantiate query object
            logger.debug("   Initializing query server")
            sm_hub.q_srv = QueryServer(ev_loop, sm_hub.lan_mac)
            await sm_hub.q_srv.initialize()
            # Instantiate api_server object
            sm_hub.api_srv = ApiServer(ev_loop, sm_hub, rt_serial)
        else:
            # Instantiate api_server object
            sm_hub.api_srv = ApiServerMin(ev_loop, sm_hub)
        # Instantiate config server object
        logger.debug("   Initializing config server")
        sm_hub.conf_srv = ConfigServer(sm_hub.api_srv)
        logger.debug("   Initializing API server")
        await sm_hub.conf_srv.initialize()  # ignore_ type
        if init_flag:
            await sm_hub.api_srv.get_initial_status()
        else:
            logger.warning("Initialization of router and modules skipped")
        startup_ok = True
    except Exception as error_msg:
        # Start failed ...
        logger.error(f"Smart Hub start failed, exception: {error_msg}")
    if not (startup_ok):
        # ... retry restarting main()
        logger.warning("Smart Hub main restarting")
        return 0

    # Initialization successfulle done, start servers
    try:
        async with sm_hub.tg:
            logger.debug("Starting API server")
            skip_init = sm_hub.tg.create_task(
                sm_hub.run_api_server(sm_hub.api_srv), name="api_srv"
            )
            if running_online:
                logger.debug("   Starting query server")
                sm_hub.tg.create_task(sm_hub.q_srv.run_query_srv(), name="q_srv")
            logger.debug("   Starting config server")
            await sm_hub.conf_srv.prepare()
            sm_hub.tg.create_task(sm_hub.conf_srv.site.start(), name="conf_srv")
            logger.info("Config server running")
    except Exception as err_msg:
        logger.error(
            f"Error starting servers, SmartHub already running? Msg: {err_msg}"
        )
        logger.warning("Program terminates in 4 s.")
        await asyncio.sleep(4)
        exit()

    # Waiting until finished
    try:
        await asyncio.wait(sm_hub.tg)  # type: ignore
    except Exception:
        pass
    if rt_serial is not None:
        rt_serial[1].close()
    if sm_hub.restart:
        return 1
    elif skip_init:
        return -1
    else:
        return 1


init_count = 0
init_flag = True
ev_loop = asyncio.new_event_loop()
while True:
    if init_count > 2:
        init_flag = False  # Restart without initialization
    term_flg = ev_loop.run_until_complete(main(ev_loop))
    if term_flg == 0:
        init_count += 1
    elif term_flg == -1:
        init_flag = False
        init_count = 0
    else:
        init_flag = True
        init_count = 0
