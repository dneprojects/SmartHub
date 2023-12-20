import logging
import asyncio
from math import ceil
from const import MirrIdx, SMGIdx, RT_CMDS, MODULE_CODES, API_RESPONSE
from hdlr_class import HdlrBase
from messages import RtResponse
from module import HbtnModule


class ModHdlr(HdlrBase):
    """Handling of module router commands."""

    def __init__(self, mod_id, api_srv) -> None:
        """Creates module handler object with serial interface"""
        self.mod_id = mod_id
        self.api_srv = api_srv
        self.msg = api_srv.hdlr.msg
        self.ser_if = self.api_srv._rt_serial
        self.logger = logging.getLogger(__name__)
        self.mod: HbtnModule = []

    def initialize(self, mod):
        """Set module properties."""
        self.mod = mod
        self.rt_id = mod.rt._id

    async def mod_reboot(self):
        """Initiates a module reboot"""
        self.logger.info(f"Module {self.mod_id} will be rebooted, please wait...")
        await self.handle_router_cmd(self.rt_id, RT_CMDS.MD_REBOOT)
        return "OK"

    async def get_module_status(self, mod_addr: int) -> bytes:
        """Get all module settings."""
        await self.api_srv.stop_opr_mode(self.rt_id)
        await self.handle_router_cmd_resp(
            self.rt_id, RT_CMDS.GET_MOD_MIRROR.replace("<mod>", chr(mod_addr))
        )
        self.mod.status = chr(mod_addr).encode() + self.rt_msg._resp_msg

    async def send_module_smg(self, mod_addr: int):
        """Send SMG data from Smart Hub to router/module."""
        await self.set_config_mode(True)
        await self.set_module_name()
        await self.set_buttons_times()
        if int(self.mod._typ[0]) in [1, 0x32, 0x0B]:
            # input related settings
            await self.set_inputs_mode()
            await self.set_analog_inputs()
        if int(self.mod._typ[0]) in [1, 0x0A]:
            # output related settings
            await self.set_logic_units()
            if self.mod._typ == "\x0a\x16":
                # dimm module specific settings
                await self.set_dimm_speed()
                await self.set_dimm_modes()
            else:
                await self.set_covers_settings()
                await self.set_covers_times()
                await self.set_blinds_times()
        if int(self.mod._typ[0]) in [1, 0x32, 0x50]:
            # motion related settings
            await self.set_motion_detection()
        if int(self.mod._typ[0]) in [1, 0x32]:
            # Smart Controller specific settings
            await self.set_module_language()
            await self.set_target_values()
            await self.set_climate_settings()
            await self.set_display_constrast()
            await self.set_temp_control()
        if int(self.mod._typ[0]) in [1]:
            # Smart Controller XL specific settings
            await self.set_dimm_speed()
            await self.set_dimm_modes()
            await self.set_supply_prio()
            await self.set_module_light()
            await self.set_limit_temperature()
        if self.mod._typ == b"\x1e\x01":
            # Ekey specific settings
            await self.set_ekey_version()
        if self.mod._typ == b"\x1e\x03":
            # GSM specific settings
            await self.set_pin()
            await self.set_logic_units()
        await self.set_config_mode(False)

    async def get_module_list(self, mod_addr: int) -> bytes:
        """Get the module description and command list."""

        await self.api_srv.stop_opr_mode(self.rt_id)
        pckg = 1
        area = 50
        cnt = 1
        mod_code = self.mod.get_module_code()
        smc_buffer = b""
        rt_command = (
            RT_CMDS.GET_MOD_SMC.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(mod_addr))
            .replace("<area>", chr(area))
            .replace("<pckg>", chr(pckg))
        )
        # Send command to router
        await self.handle_router_cmd_resp(self.rt_id, rt_command)
        resp = self.rt_msg._resp_msg

        if len(resp) <= 1:
            self.logger.debug(f"Empty SMC for module {chr(mod_addr)}")
        else:
            smc_buffer += resp[1:]
            len_SMC_file = int.from_bytes(resp[3:5], "little")
            pckg_cnt = int(ceil(len_SMC_file / 31))
            while cnt < pckg_cnt:
                await asyncio.sleep(0.2)
                cnt += 1
                pckg = resp[0]
                pckg += 1
                if pckg == 0:
                    area += 1
                if area == 100:
                    self.logger.error("Content of module will be deleted!")
                rt_command = (
                    RT_CMDS.GET_MOD_SMC.replace("<rtr>", chr(self.rt_id))
                    .replace("<mod>", chr(mod_addr))
                    .replace("<area>", chr(area))
                    .replace("<pckg>", chr(pckg))
                )
                # Send command to router
                await self.handle_router_cmd_resp(self.rt_id, rt_command)
                resp = self.rt_msg._resp_msg
                if resp[0] == pckg:
                    smc_buffer += resp[1:]
                else:
                    self.logger.debug(f"SMC package {resp[0]} read again, discarded")
                    cnt -= 1
        return smc_buffer

    async def send_module_list(self, mod_addr: int):
        """Send SMC data from Smart Hub to router/module."""
        await self.handle_router_cmd_resp(self.rt_id, RT_CMDS.STOP_MIRROR)
        mod_list = self.mod.list_upload
        resp_flg = 0
        l_len = len(mod_list)
        l_cnt = 0
        flg = chr(6)
        cnt = 1
        while l_cnt < l_len:
            l_pckg = mod_list[l_cnt : l_cnt + min(12, l_len - l_cnt)]
            l_p = len(l_pckg)
            cmd = (
                RT_CMDS.SEND_MOD_SMC.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(mod_addr))
                .replace("<len>", chr(l_p + 10))
                .replace("<l4>", chr(l_p + 6))
            )
            cmd += flg + chr(cnt) + l_pckg.decode("iso8859-1") + "\xff"
            await self.handle_router_cmd_resp(self.rt_id, cmd)
            flg = chr(7)
            resp_cnt = self.rt_msg._resp_buffer[-2]
            resp_flg = self.rt_msg._resp_buffer[-3]
            if resp_cnt == cnt:
                cnt += 1
                l_cnt += l_p
            elif resp_flg == 8:
                cnt += 1
                l_cnt += l_p
            self.logger.debug(
                f"List upload (SMC) returned: Count {cnt} Flag {resp_flg}"
            )
            await asyncio.sleep(0.5)
        self.logger.info(
            f"List upload (SMC) terminated: Count {resp_cnt} Flag {resp_flg}"
        )
        return

    async def set_module_language(self):
        """Send language settings to module."""
        base_idx = SMGIdx.index(MirrIdx.MOD_LANG)
        lang = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_MOD_LANG.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<lang>", chr(lang))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_module_name(self):
        """Send module name to module."""
        base_idx = SMGIdx.index(MirrIdx.MOD_NAME)
        md_name = self.mod.smg_upload[base_idx : base_idx + 32]
        self.mod._name = md_name.decode("iso8859-1").strip()
        for cnt in range(4):
            cmd = (
                RT_CMDS.SET_MOD_NAME.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<cnt>", chr(cnt * 8))
                .replace("<name8>", md_name[cnt * 8 : cnt * 8 + 8].decode("iso8859-1"))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
            await asyncio.sleep(0.1)
        return "OK"

    async def set_display_constrast(self):
        """Send display contrast setting to module."""
        base_idx = SMGIdx.index(MirrIdx.DISPL_CONTR)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_DISPL_CONTR.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_inputs_mode(self):
        """Send display contrast setting to module."""
        base_idx = SMGIdx.index(MirrIdx.SWMOD_1_8)
        i1 = self.mod.smg_upload[base_idx]
        i9 = self.mod.smg_upload[base_idx + 1]
        i17 = self.mod.smg_upload[base_idx + 2]
        cmd = (
            RT_CMDS.SET_INP_MODES.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<i_1_8>", chr(i1))
            .replace("<i_9_16>", chr(i9))
            .replace("<i_17_24>", chr(i17))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_buttons_times(self):
        """Send display contrast setting to module."""
        base_idx = SMGIdx.index(MirrIdx.T_SHORT)
        ts = self.mod.smg_upload[base_idx]
        base_idx = SMGIdx.index(MirrIdx.T_LONG)
        tl = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_INP_TIMES.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<tshrt>", chr(ts))
            .replace("<tlng>", chr(tl))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_covers_settings(self):
        base_idx = SMGIdx.index(MirrIdx.COVER_SETTINGS)
        """Send cover settings to module."""
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_COVER_SETTGS.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_covers_times(self):
        """Send cover time to module."""
        if int(self.mod._typ[0]) == 1:
            no_covers = 5
        else:
            no_covers = 4
        base_idx = SMGIdx.index(MirrIdx.COVER_T)
        for ci in range(no_covers):
            t_a = self.mod.smg_upload[2 * ci + base_idx]
            t_b = self.mod.smg_upload[2 * ci + base_idx + 1]
            time_a, time_b, interp = self.mod.encode_cover_settings(t_a, t_b)
            cmd = (
                RT_CMDS.SET_COVER_TIME.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<sob>", chr(1))
                .replace("<int>", chr(interp))
                .replace("<out>", chr(ci + 1))
                .replace("<vala>", chr(time_a))
                .replace("<valb>", chr(time_b))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_blinds_times(self):
        """Send blind time to module."""
        if int(self.mod._typ[0]) == 1:
            no_covers = 5
        else:
            no_covers = 4
        base_idx = SMGIdx.index(MirrIdx.BLAD_T)
        for ci in range(no_covers):
            t_a = self.mod.smg_upload[2 * ci + base_idx]
            t_b = self.mod.smg_upload[2 * ci + base_idx + 1]
            cmd = (
                RT_CMDS.SET_COVER_TIME.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<sob>", chr(2))
                .replace("<int>", chr(0))
                .replace("<out>", chr(ci + 1))
                .replace("<vala>", chr(t_a))
                .replace("<valb>", chr(t_b))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_logic_units(self):
        """Send logic settings to module."""
        base_idx = SMGIdx.index(MirrIdx.LOGIC)
        for l_u in range(10):
            val = self.mod.smg_upload[base_idx + l_u * 2 : base_idx + l_u * 2 + 2]
            cmd = (
                RT_CMDS.SET_LOGIC_UNIT.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<lno>", chr(l_u + 1))
                .replace("<md>", chr(val[0]))
                .replace("<act>", chr(val[1]))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_analog_inputs(self):
        """Send AD settings to module."""
        base_idx = SMGIdx.index(MirrIdx.STAT_AD24_ACTIVE)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_AD.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_motion_detection(self):
        """Send motion detection settings to module."""
        lvl_idx = SMGIdx.index(MirrIdx.MOV_LVL)
        tim_idx = SMGIdx.index(MirrIdx.MOV_TIME)
        led_idx = SMGIdx.index(MirrIdx.LED_I)
        lvl = self.mod.smg_upload[lvl_idx]
        tim = self.mod.smg_upload[tim_idx]
        led = self.mod.smg_upload[led_idx]

        cmd = (
            RT_CMDS.SET_MOT_DET.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<lvl>", chr(lvl))
            .replace("<tim>", chr(tim))
            .replace("<led>", chr(led))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_dimm_speed(self):
        """Send dimm speed settings to module."""
        base_idx = SMGIdx.index(MirrIdx.T_DIM)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_DIMM_SPEED.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<tdim>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_dimm_modes(self):
        """Send dimm mode settings to module."""
        base_idx = SMGIdx.index(MirrIdx.DIMM_MODE)
        if len(self.mod.smg_upload) <= base_idx:
            # no dimm mode available
            return "OK"
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_DIMM_MODES.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<msk>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_target_values(self):
        """Send target value settings to module."""
        for t_i in range(2):
            base_idx = SMGIdx.index(MirrIdx.T_SETP_1) + t_i
            val_lo = self.mod.smg_upload[base_idx]
            val_hi = self.mod.smg_upload[base_idx + 1]
            cmd = (
                RT_CMDS.SET_TEMP.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<sel>", chr(t_i + 1))
                .replace("<tmpl>", chr(val_lo))
                .replace("<tmph>", chr(val_hi))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_climate_settings(self):
        """Send climate settings to module."""
        base_idx = SMGIdx.index(MirrIdx.CLIM_SETTINGS)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_CLIMATE.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_temp_control(self):
        """Send temperature controller 1 or 2 setting to module."""
        base_idx = SMGIdx.index(MirrIdx.TMP_CTL_MD)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_T1_OR_T2.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_supply_prio(self):
        """Send supply priority settings to module."""
        base_idx = SMGIdx.index(MirrIdx.SUPPLY_PRIO)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_MOD_SUPPLY.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<set>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_module_light(self):
        """Send module light time setting to module."""
        base_idx = SMGIdx.index(MirrIdx.MOD_LIGHT_TIM)
        val = self.mod.smg_upload[base_idx]
        cmd = (
            RT_CMDS.SET_MOD_T_LIGHT.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<tim>", chr(val))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_limit_temperature(self):
        """Send limit temperature settings to module."""
        base_idx = SMGIdx.index(MirrIdx.T_LIM)
        val_l = self.mod.smg_upload[base_idx]
        val_h = self.mod.smg_upload[base_idx + 1]
        cmd = (
            RT_CMDS.SET_T_LIM.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<Tlow>", chr(val_l))
            .replace("<Thigh>", chr(val_h))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_pin(self):
        """Send pin settings to module."""
        p1_idx = SMGIdx.index(MirrIdx.COVER_T)  # 1a
        p3_idx = p1_idx + 3  # 2b
        p4_idx = p1_idx + 6  # 4a
        p2_idx = p3_idx + 3  # 5b
        p1 = (self.mod.smg_upload[p1_idx] / 9) - 9
        p2 = (((self.mod.smg_upload[p2_idx] / 2) + 88) / 10) - 10
        p3 = (self.mod.smg_upload[p3_idx] / 7) - 4
        p4 = self.mod.smg_upload[p4_idx]
        if p1 >= 10 | p2 >= 10 | p3 >= 10 | p4 >= 10:
            self.logger.error(f"Error decoding pin for module {self.mod._id}.")
            return "ERROR"
        cmd = (
            RT_CMDS.SET_PIN.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<p1>", chr(p1))
            .replace("<p2>", chr(p2))
            .replace("<p3>", chr(p3))
            .replace("<p4>", chr(p4))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_ekey_version(self):
        """Send Ekey version settings to module."""
        base_idx = SMGIdx.index(MirrIdx.DISPL_CONTR)
        val = self.mod.smg_upload[base_idx]
        await self.switch_ekey_version(val)
        return "OK"

    async def switch_ekey_version(self, vers):
        """Directly set Ekey version in module."""
        cmd = (
            RT_CMDS.SET_EKEY_VERS.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<ver>", chr(vers))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_ekey_teach_mode(self, user, finger, time):
        """Send Ekey teaching mode settings to module."""
        cmd = (
            RT_CMDS.SET_EKEY_TEACH.replace("<rtr>", chr(self.rt_id))
            .replace("<mod>", chr(self.mod_id))
            .replace("<usr>", chr(user))
            .replace("<fgr>", chr(finger))
            .replace("<tim>", chr(time))
        )
        await self.handle_router_cmd(self.rt_id, cmd)
        return "OK"

    async def ekey_db_read(self):
        """Transfer ekey database to fanser and hub."""
        # Transfer to fanser
        cmd = RT_CMDS.GET_EKEY_TO_FANS.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        # Transfer to hub in packages of 24 bytes
        pkg_cnt = 0
        db_buffer = b""
        db_upload_ready = False
        cmd = RT_CMDS.GET_EKEY_TO_HUB.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        while not db_upload_ready:
            await asyncio.sleep(0.2)
            await self.handle_router_cmd_resp(
                self.rt_id, cmd.replace("<pkg>", chr(pkg_cnt))
            )
            pkg_resp = self.rt_msg._resp_buffer[10]
            db_size = self.rt_msg._resp_buffer[12] * 256 + self.rt_msg._resp_buffer[11]
            buf_len = self.rt_msg._resp_buffer[7] - 7
            db_buffer += self.rt_msg._resp_buffer[13:-1]
            db_upload_ready = len(db_buffer) >= db_size - 24
            pkg_cnt += 1
        return db_buffer

    async def del_ekey_entry(self, user, finger):
        """Send Ekey delete command for a single entry to module."""
        if finger == 255:
            fingers = [*range(1, 11)]
        else:
            fingers = [finger]
        for fngr in fingers:
            cmd = (
                RT_CMDS.DEL_EKEY_1.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<usr>", chr(user))
                .replace("<fgr>", chr(fngr))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def del_ekey_list(self, no_users, list):
        """Send Ekey delete command for a single entry to module."""
        if no_users > 1:
            return "ERROR"
        user_id = list[1]
        no_fingers = list[2]
        fingers = list[3:]
        for fngr in fingers:
            cmd = (
                RT_CMDS.DEL_EKEY_1.replace("<rtr>", chr(self.rt_id))
                .replace("<mod>", chr(self.mod_id))
                .replace("<usr>", chr(user_id))
                .replace("<fgr>", chr(fngr))
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
            await asyncio.sleep(1)
        return "OK"

    async def del_ekey_all_users(self):
        """Send Ekey delete command for a single entry to module."""

        cmd = RT_CMDS.DEL_EKEY_ALL.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def ekey_log_read(self):
        """Reads Ekey log from module."""
        # API return 50/1/9 value 1: running or 2: finished
        cmd = RT_CMDS.GET_EKEY_LOG_STRT.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        log_len = int.from_bytes(self.rt_msg._resp_msg[2:4], "little") * 8
        log_len_low = log_len & 0x0FF
        log_len_high = (log_len >> 8) & 0x0FF
        resp = (chr(self.mod_id) + chr(log_len_low) + chr(log_len_high)).encode(
            "iso8859-1"
        )
        resp += self.rt_msg._resp_msg[4:]  # length + content
        cont_reading = True
        while cont_reading:
            cmd = RT_CMDS.GET_EKEY_LOG_REST.replace("<rtr>", chr(self.rt_id)).replace(
                "<mod>", chr(self.mod_id)
            )
            await self.handle_router_cmd_resp(self.rt_id, cmd)
            cnt = int.from_bytes(self.rt_msg._resp_msg[2:4], "little")
            if cnt > 0:
                resp += self.rt_msg._resp_msg[4:]
            else:
                cont_reading = False
        return resp

    async def ekey_log_delete(self):
        """Deletes Ekey log on module."""
        cmd = RT_CMDS.RES_EKEY_LOG.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def set_ekey_pairing(self):
        """Set Ekey module into paring mode."""
        cmd = RT_CMDS.SET_EKEY_PAIR.replace("<rtr>", chr(self.rt_id)).replace(
            "<mod>", chr(self.mod_id)
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return "OK"

    async def get_ekey_status(self):
        """Upload Ekey status from module."""
        cmd = RT_CMDS.GET_EKEY_STAT.replace("<mod>", chr(self.mod_id))
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        return self.rt_msg._resp_msg

    async def get_air_quality(self):
        """Read module air quality values."""
        await self.set_config_mode(True)
        cmd = RT_CMDS.GET_AIR_QUAL.replace("<mod>", chr(self.mod_id))
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        resp = self.rt_msg._resp_buffer[-10:-1]
        await self.set_config_mode(False)
        if resp[-5:] == f"\x44{chr(self.mod_id)}\x05\xfa\x02".encode("iso8859-1"):
            resp = "ERROR_250_2"
        return resp

    async def calibrate_air_quality(
        self, perc_good: int, val_good: int, perc_bad: int, val_bad: int
    ):
        """Read module air quality values."""
        await self.set_config_mode(True)
        cmd = (
            RT_CMDS.CAL_AIR_QUAL.replace("<mod>", chr(self.mod_id))
            .replace("<prc_good>", chr(perc_good))
            .replace("<good_long>", chr(val_good & 0xFF) + chr(val_good >> 8))
            .replace("<prc_bad>", chr(perc_bad))
            .replace("<bad_long>", chr(val_bad & 0xFF) + chr(val_bad >> 8))
        )
        await self.handle_router_cmd_resp(self.rt_id, cmd)
        resp = self.rt_msg._resp_buffer[-10:-1]
        await self.set_config_mode(False)
        if resp[-5:] == f"\x44{chr(self.mod_id)}\x05\xfa\x02".encode("iso8859-1"):
            resp = "ERROR_250_2"
        return resp

    async def set_config_mode(self, flg: bool):
        """Forward to own router."""
        await self.api_srv.routers[self.rt_id - 1].set_config_mode(flg)
