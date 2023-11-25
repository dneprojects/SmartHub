from const import (
    EventCodes,
    ActionCodes,
)


class AutomationDefinition:
    """Object with automation data and methods."""

    def __init__(self, atm_def):
        """Fill all properties with automation's values."""
        if isinstance(atm_def, bytes):
            self.src_rt = int(atm_def[0])
            self.src_mod = int(atm_def[1])
            self.event_code = int(atm_def[2])
            self.event_arg1 = int(atm_def[3])
            self.event_arg2 = int(atm_def[4])
            self.condition = int(atm_def[6])
            self.action_code = int(atm_def[7])
            self.action_args = []
            for a in atm_def[8:]:
                self.action_args.append(int(a))

    def event_name(self) -> str:
        """Return event name."""
        return EventCodes[self.event_code]

    def event_description(self):
        """Parse event arguments."""
        event_name = self.event_name()
        event_arg = self.event_arg1
        event_arg2 = self.event_arg2
        if event_name == "Merker/Logik":
            if event_arg == 0:
                set_str = " rückgesetzt"
            else:
                set_str = " gesetzt"
            event_arg += self.event_arg2  # one is always zero
            event_arg2 = ""
            if event_arg in range(1, 17):
                event_name = "Lokaler Merker" + set_str
            elif event_arg in range(33, 49):
                event_name = "Globaler Merker" + set_str
                event_arg -= 32
            elif event_arg in range(81, 91):
                event_name = "Logikausgang" + set_str
                event_arg -= 80
            else:
                for cnt_i in range(10):
                    if event_arg in range(96 + cnt_i * 16, 96 + (cnt_i + 1) * 16):
                        event_name = f"Counter {cnt_i + 1} Wert erreicht"
                        event_arg2 = event_arg - 95 - cnt_i * 16
                        event_arg = cnt_i + 1
                        break
        elif event_name == "Modusänderung":
            event_name = "Modus neu: "
            if self.event_arg2 == 1:
                event_name += "Tag"
            elif self.event_arg2 == 2:
                event_name += "Nacht"
            elif self.event_arg2 == 4:
                event_name += "Alarm"
            elif self.event_arg2 == 16:
                event_name += "Abwesend"
            if self.event_arg2 == 32:
                event_name += "Anwesend"
            if self.event_arg2 == 48:
                event_name += "Schlafen"
            if self.event_arg2 == 80:
                event_name += "Sommer"
            if self.event_arg2 == 96:
                event_name += "User1"
            if self.event_arg2 == 112:
                event_name += "User2"
            event_arg = ""
            event_arg2 = ""
        elif self.event_arg2 == 0:
            event_arg2 = ""
        return event_name, event_arg, event_arg2

    def action_name(self) -> str:
        """Return action name."""
        return ActionCodes[self.action_code]

    def make_definition(self) -> bytes:
        """Return definition line as bytes."""
        def_line = (
            chr(self.src_rt)
            + chr(self.src_mod)
            + chr(self.event_code)
            + chr(self.event_arg1)
            + chr(self.event_arg2)
            + chr(len(self.action_args) + 8)
            + chr(self.condition)
            + chr(self.action_code)
        )
        for actn_arg in self.action_args:
            def_line += chr(actn_arg)
        return def_line.encode("iso8859-1")
