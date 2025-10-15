from abc import ABC, abstractmethod

from mypylib.mypylib import MyPyClass


class MtcModule(ABC):

    description = ''  # module text description
    default_value = True  # is module enabled by default

    def __init__(self, ion, local, *args, **kwargs):
        from myioncore.myioncore import MyIonCore
        self.ion: MyIonCore = ion
        self.local: MyPyClass = local

    @abstractmethod
    def add_console_commands(self, console):  ...

    @classmethod
    def check_enable(cls, ion: "MyIonCore"):
        return

    def check_disable(self):
        return
