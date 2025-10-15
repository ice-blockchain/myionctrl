import psutil

from modules.module import MtcModule


class LiteserverModule(MtcModule):

    description = 'For liteserver usage only without validator.'
    default_value = False

    @classmethod
    def check_enable(cls, ion: "MyIonCore"):
        if ion.using_validator():
            raise Exception(f'Cannot enable liteserver mode while validator mode is enabled. '
                            f'Use `disable_mode validator` first.')

    def add_console_commands(self, console):
        ...
