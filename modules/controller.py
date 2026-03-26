import json
import os
import time

from mypylib.mypylib import color_print, print_table
from myionctrl.console_cmd import add_command, check_usage_one_arg, check_usage_two_args, check_usage_args_min_max_len

from myionctrl.utils import GetItemFromList
from modules.module import MtcModule

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from myioncore import MyIonCore


class ControllerModule(MtcModule):

    description = 'Liquid staking controllers.'
    default_value = False

    def do_create_controllers(self):
        new_controllers = self.ion.GetControllers()
        old_controllers = self.ion.local.db.get("using_controllers", list())
        if new_controllers == old_controllers:
            return

        self.ion.local.add_log("start CreateControllers function", "debug")
        wallet = self.ion.GetValidatorWallet()
        liquid_pool_addr = self.ion.GetLiquidPoolAddr()
        contract_path = self.ion.contractsDir + "jetton_pool/"
        if not os.path.isdir(contract_path):
            self.ion.DownloadContract("https://github.com/igroman787/jetton_pool")

        file_name0 = contract_path + "fift-scripts/deploy_controller0.boc"
        file_name1 = contract_path + "fift-scripts/deploy_controller1.boc"
        result_file_path0 = self.ion.SignBocWithWallet(wallet, file_name0, liquid_pool_addr, 4)
        self.ion.SendFile(result_file_path0, wallet)
        time.sleep(10)
        result_file_path1 = self.ion.SignBocWithWallet(wallet, file_name1, liquid_pool_addr, 4)
        self.ion.SendFile(result_file_path1, wallet)

        self.ion.local.db["old_controllers"] = old_controllers
        self.ion.local.db["using_controllers"] = new_controllers
        self.ion.local.save()

    def create_controllers(self, args):
        self.do_create_controllers()
        color_print("CreateControllers - {green}OK{endc}")

    def print_controllers_list(self, args):
        new_controllers = self.ion.GetControllers()
        using_controllers = self.ion.GetSettings("using_controllers")
        old_controllers = self.ion.GetSettings("old_controllers")
        user_controllers_list = self.ion.GetSettings("user_controllers_list")
        print("using controllers:")
        if using_controllers is not None:
            self.print_controllers_list_process(using_controllers)
        if new_controllers is not None and new_controllers != using_controllers:
            print()
            print("new controllers:")
            self.print_controllers_list_process(new_controllers)
        if old_controllers is not None and len(old_controllers) > 0:
            print()
            print("old controllers:")
            self.print_controllers_list_process(old_controllers)
        if user_controllers_list is not None and len(user_controllers_list) > 0:
            print()
            print("user controllers:")
            self.print_controllers_list_process(user_controllers_list)

    def print_controllers_list_process(self, controllers):
        table = list()
        table += [["Address", "Status", "Balance", "Approved", "State"]]
        for controllerAddr in controllers:
            account = self.ion.GetAccount(controllerAddr)
            controllerData = self.ion.GetControllerData(controllerAddr)
            approved = True if controllerData and controllerData["approved"] == -1 else False
            state = controllerData["state"] if controllerData else None
            table += [[controllerAddr, account.status, account.balance, approved, state]]
        print_table(table)

    def get_controller_data(self, args):
        if not check_usage_one_arg("get_controller_data", args):
            return
        controller_addr = args[0]
        controller_data = self.ion.GetControllerData(controller_addr)
        print(json.dumps(controller_data, indent=4))

    def do_deposit_to_controller(self, controller_addr, amount):
        self.ion.local.add_log("start DepositToController function", "debug")
        wallet = self.ion.GetValidatorWallet()
        file_name = self.ion.contractsDir + "jetton_pool/fift-scripts/top-up.boc"
        result_file_path = self.ion.SignBocWithWallet(wallet, file_name, controller_addr, amount)
        self.ion.SendFile(result_file_path, wallet)

    def deposit_to_controller(self, args):
        if not check_usage_two_args("deposit_to_controller", args):
            return
        controller_addr = args[0]
        amount = float(args[1])
        self.do_deposit_to_controller(controller_addr, amount)

    def withdraw_from_controller(self, args):
        if not check_usage_args_min_max_len("withdraw_from_controller", args, min_len=1, max_len=2):
            return
        controller_addr = args[0]
        amount = GetItemFromList(args, 1)
        self.ion.WithdrawFromController(controller_addr, amount)

    def calculate_annual_controller_percentage(self, args):
        if not check_usage_args_min_max_len("calculate_annual_controller_percentage", args, min_len=0, max_len=1):
            return
        if args:
            percent_per_round = float(args[0])
        else:
            percent_per_round = self.ion.GetSettings("max_interest_percent")
        config15 = self.ion.GetConfig(15)
        roundPeriod = config15["validators_elected_for"]
        rounds = 365 * 24 * 3600 / roundPeriod
        yearInterest = (1 + percent_per_round / 100) * rounds
        yearInterestPercent = round(yearInterest / 100, 2)
        print("roundPeriod", roundPeriod)
        print("rounds", rounds)
        print("percentPerRound", percent_per_round)
        print("yearInterest", yearInterest)
        print(f"yearInterestPercent: {yearInterestPercent}%")

    def controller_update_validator_set(self, args):
        if not check_usage_one_arg("controller_update_validator_set", args):
            return
        controller_addr = args[0]
        self.ion.ControllerUpdateValidatorSet(controller_addr)
        color_print("ControllerUpdateValidatorSet - {green}OK{endc}")

    def do_stop_controller(self, controller_addr):
        stop_controllers_list = self.ion.local.db.get("stop_controllers_list")
        if stop_controllers_list is None:
            stop_controllers_list = list()
        if controller_addr not in stop_controllers_list:
            stop_controllers_list.append(controller_addr)
        self.ion.local.db["stop_controllers_list"] = stop_controllers_list

        user_controllers = self.ion.local.db.get("user_controllers")
        if user_controllers is not None and controller_addr in user_controllers:
            user_controllers.remove(controller_addr)
        self.ion.local.save()

    def stop_controller(self, args):
        if not check_usage_one_arg("stop_controller", args):
            return
        controller_addr = args[0]
        self.do_stop_controller(controller_addr)
        color_print("StopController - {green}OK{endc}")

    def stop_and_withdraw_controller(self, args):
        if not check_usage_args_min_max_len("stop_and_withdraw_controller", args, min_len=1, max_len=2):
            return
        controller_addr = args[0]
        amount = GetItemFromList(args, 1)
        if amount is None:
            account = self.ion.GetAccount(controller_addr)
            amount = account.balance - 10.1
        self.do_stop_controller(controller_addr)
        self.ion.WithdrawFromController(controller_addr, amount)
        color_print("StopAndWithdrawController - {green}OK{endc}")

    def do_add_controller(self, controller_addr):
        user_controllers = self.ion.local.db.get("user_controllers")
        if user_controllers is None:
            user_controllers = list()
        if controller_addr not in user_controllers:
            user_controllers.append(controller_addr)
        self.ion.local.db["user_controllers"] = user_controllers

        stop_controllers_list = self.ion.local.db.get("stop_controllers_list")
        if stop_controllers_list is not None and controller_addr in stop_controllers_list:
            stop_controllers_list.remove(controller_addr)
        self.ion.local.save()

    def add_controller(self, args):
        if not check_usage_one_arg("add_controller", args):
            return
        controller_addr = args[0]
        self.do_add_controller(controller_addr)
        color_print("AddController - {green}OK{endc}")

    def do_check_liquid_pool(self):
        liquid_pool_addr = self.ion.GetLiquidPoolAddr()
        account = self.ion.GetAccount(liquid_pool_addr)
        history = self.ion.GetAccountHistory(account, 5000)
        addrs_list = list()
        for message in history:
            if message.srcAddr is None or message.value is None:
                continue
            src_addr_full = f"{message.srcWorkchain}:{message.srcAddr}"
            dest_add_full = f"{message.destWorkchain}:{message.destAddr}"
            if src_addr_full == account.addrFull:
                fromto = dest_add_full
            else:
                fromto = src_addr_full
            fromto = self.ion.AddrFull2AddrB64(fromto)
            if fromto not in addrs_list:
                addrs_list.append(fromto)

        for controllerAddr in addrs_list:
            account = self.ion.GetAccount(controllerAddr)
            version = self.ion.GetVersionFromCodeHash(account.codeHash)
            if version is None or "controller" not in version:
                continue
            print(f"check controller: {controllerAddr}")
            self.ion.ControllerUpdateValidatorSet(controllerAddr)

    def check_liquid_pool(self, args):
        self.do_check_liquid_pool()
        color_print("CheckLiquidPool - {green}OK{endc}")

    def do_calculate_loan_amount_test(self):
        min_loan = self.ion.local.db.get("min_loan", 41000)
        max_loan = self.ion.local.db.get("max_loan", 43000)
        max_interest_percent = self.ion.local.db.get("max_interest_percent", 1.5)
        max_interest = int(max_interest_percent / 100 * 16777216)
        return self.ion.CalculateLoanAmount(min_loan, max_loan, max_interest)

    def calculate_loan_amount_test(self, args):
        t = self.do_calculate_loan_amount_test()
        print(t)

    @classmethod
    def check_enable(cls, ion: "MyIonCore"):
        from myioninstaller.settings import enable_ion_http_api
        enable_ion_http_api(ion.local)

    def add_console_commands(self, console):
        add_command(self.local, console, "create_controllers", self.create_controllers)
        add_command(self.local, console, "update_controllers", self.create_controllers)
        add_command(self.local, console, "controllers_list", self.print_controllers_list)
        add_command(self.local, console, "get_controller_data", self.get_controller_data)
        add_command(self.local, console, "deposit_to_controller", self.deposit_to_controller)
        add_command(self.local, console, "withdraw_from_controller", self.withdraw_from_controller)
        add_command(self.local, console, "calculate_annual_controller_percentage", self.calculate_annual_controller_percentage)
        add_command(self.local, console, "controller_update_validator_set", self.controller_update_validator_set)
        add_command(self.local, console, "stop_controller", self.stop_controller)
        add_command(self.local, console, "stop_and_withdraw_controller", self.stop_and_withdraw_controller)
        add_command(self.local, console, "add_controller", self.add_controller)
        add_command(self.local, console, "check_liquid_pool", self.check_liquid_pool)
        add_command(self.local, console, "test_calculate_loan_amount", self.calculate_loan_amount_test)
