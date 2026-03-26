from modules.module import MtcModule


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from myioncore import MyIonCore


class LiteserverModule(MtcModule):

    description = 'For liteserver usage only without validator.'
    default_value = False

    @classmethod
    def check_enable(cls, ion: "MyIonCore"):
        if ion.using_validator():
            raise Exception('Cannot enable liteserver mode while validator mode is enabled. '
                            'Use `disable_mode validator` first.')

    def add_console_commands(self, console):
        ...
