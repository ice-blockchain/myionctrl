import io
from contextlib import redirect_stdout, redirect_stderr
import os
import pytest
from typing import Protocol

from mypyconsole.mypyconsole import MyPyConsole
from myioncore.myioncore import MyIonCore
from myionctrl.myionctrl import Init
from mypylib.mypylib import MyPyClass, dir as ensure_dir, Dict
from tests.helpers import remove_colors


class TestLocal(MyPyClass):
    def __init__(self, file_path: str, work_dir: str, temp_dir: str):
        self._work_dir = work_dir
        self._temp_dir = temp_dir
        super().__init__(file_path)

    def get_my_work_dir(self):
        return ensure_dir(self._work_dir)

    def get_my_temp_dir(self):
        return ensure_dir(self._temp_dir)

    def self_test(self):
        pass

    # def write_db(self, data):
    #     self.buffer.old_db = Dict(self.db)
    #
    # def load_db(self, db_path=False):
    #     self.set_default_config()
    #     return True

    def write_log(self):
        pass


@pytest.fixture()
def local(tmp_path):
    work_dir = str(tmp_path / "work")
    temp_dir = str(tmp_path / "tmp")
    file_path = str(tmp_path / "tests_runner.py")
    os.makedirs(work_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    local = TestLocal(file_path=file_path, work_dir=work_dir, temp_dir=temp_dir)

    local.db["liteClient"] = {
      "appPath": "/usr/bin/ion/lite-client/lite-client",
      "configPath": "/usr/bin/ion/global.config.json",
      "liteServer": {
        "pubkeyPath": "/var/ion-work/keys/liteserver.pub",
        "ip": "127.0.0.1",
        "port": 33333
      }
    }
    local.db["validatorConsole"] = {
      "appPath": "/usr/bin/ion/validator-engine-console/validator-engine-console",
      "privKeyPath": "/var/ion-work/keys/client",
      "pubKeyPath": "/var/ion-work/keys/server.pub",
      "addr": "127.0.0.1:44444"
    }
    local.db["fift"] = {
      "appPath": "/usr/bin/ion/crypto/fift",
      "libsPath": "/usr/src/ion/crypto/fift/lib",
      "smartcontsPath": "/usr/src/ion/crypto/smartcont"
    }
    return local


@pytest.fixture()
def ion(local, monkeypatch):
    monkeypatch.setattr(MyIonCore, "create_self_db_backup", lambda self: None)
    monkeypatch.setattr(MyIonCore, "GetNetworkName", lambda self: "mainnet")
    monkeypatch.setattr(TestLocal, 'save', lambda *args, **kwargs: None)
    return MyIonCore(local)


class ConsoleProtocol(Protocol):

    def execute(self, command: str, no_color: bool = False) -> str:
        ...


class TestMyPyConsole(MyPyConsole):

    def run_pre_up(self, no_color: bool = False):
        output = io.StringIO()
        with redirect_stderr(output), redirect_stdout(output):
            self.startFunction()
            output = output.getvalue()
            if no_color:
                output = remove_colors(output)
            return output

    def execute(self, command: str, no_color: bool = False) -> str:
        output = io.StringIO()
        with redirect_stderr(output), redirect_stdout(output):
            self.user_worker = lambda: command
            self.get_cmd_from_user()
            output = output.getvalue()
            if no_color:
                output = remove_colors(output)
            return output


@pytest.fixture()
def cli(local, ion) -> TestMyPyConsole:
    console = TestMyPyConsole()
    mp = pytest.MonkeyPatch()
    mp.setattr(MyIonCore, "using_pool", lambda self: True)
    mp.setattr(MyIonCore, "using_nominator_pool", lambda self: True)
    mp.setattr(MyIonCore, "using_single_nominator", lambda self: True)
    Init(local, ion, console, argv=[])
    mp.undo()
    # console.debug = True
    return console
