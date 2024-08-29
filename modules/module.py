from abc import ABC, abstractmethod


class MtcModule(ABC):

    description = ''  # module text description
    default_value = True  # is module enabled by default

    def __init__(self, ion, local, *args, **kwargs):
        from myioncore.myioncore import MyTonCore
        self.ion: MyTonCore = ion
        self.local = local

    @abstractmethod
    def add_console_commands(self, console):  ...
