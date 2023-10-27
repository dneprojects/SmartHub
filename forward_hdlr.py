from const import API_FORWARD as fspec
from hdlr_class import HdlrBase


class ForwardHdlr(HdlrBase):
    """Handling of all actions messages."""

    async def process_message(self):
        """Parse message, prepare and send router command"""

        match self._spec:
            case fspec.SMHUB_FWD:
                print("Forwarded message")
            case _:
                self.response = "Unknown API forward command"
                print(self.response)
                return

        # Send command to router
        await self.send_router_cmd()

        print(self.response)
