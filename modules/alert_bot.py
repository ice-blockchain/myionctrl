import dataclasses
import time
import requests

from modules.module import MtcModule
from mypylib.mypylib import get_timestamp, print_table, color_print
from myioncore import get_hostname
from myionctrl.utils import timestamp2utcdatetime


@dataclasses.dataclass
class Alert:
    severity: str
    text: str
    timeout: int


HOUR = 3600
VALIDATION_PERIOD = 65536
FREEZE_PERIOD = 32768
ELECTIONS_START_BEFORE = 8192


ALERTS = {}


def init_alerts():
    global ALERTS
    ALERTS = {
        "low_wallet_balance": Alert(
            "low",
            "Validator wallet {wallet} balance is low: {balance} ION.",
            18 * HOUR
        ),
        "db_usage_80": Alert(
            "high",
            """ION DB usage > 80%. Clean the ION database: 
            https://docs.ice.io/participate/nodes/node-maintenance-and-security#database-grooming 
            or (and) set node\'s archive ttl to lower value.""",
            24 * HOUR
        ),
        "db_usage_95": Alert(
            "critical",
            """ION DB usage > 95%. Disk is almost full, clean the ION database immediately: 
            https://docs.ice.io/participate/nodes/node-maintenance-and-security#database-grooming 
            or (and) set node\'s archive ttl to lower value.""",
            6 * HOUR
        ),
        "low_efficiency": Alert(
            "high",
            """Validator efficiency is low: {efficiency}%.""",
            VALIDATION_PERIOD // 3
        ),
        "out_of_sync": Alert(
            "critical",
            "Node is out of sync on {sync} sec.",
            300
        ),
        "service_down": Alert(
            "critical",
            "validator.service is down.",
            300
        ),
        "adnl_connection_failed": Alert(
            "high",
            "ADNL connection to node failed",
            3 * HOUR
        ),
        "zero_block_created": Alert(
            "critical",
            "Validator has not created any blocks in the last {hours} hours.",
            VALIDATION_PERIOD // 3
        ),
        "validator_slashed": Alert(
            "high",
            "Validator has been slashed in previous round for {amount} ION",
            FREEZE_PERIOD
        ),
        "stake_not_accepted": Alert(
            "high",
            "Validator's stake has not been accepted",
            ELECTIONS_START_BEFORE
        ),
        "stake_accepted": Alert(
            "info",
            "Validator's stake {stake} ION has been accepted",
            ELECTIONS_START_BEFORE
        ),
        "stake_returned": Alert(
            "info",
            "Validator's stake {stake} ION has been returned on address {address}. The reward amount is {reward} ION.",
            60
        ),
        "stake_not_returned": Alert(
            "high",
            "Validator's stake has not been returned on address {address}.",
            60
        ),
        "voting": Alert(
            "high",
            "Found proposals with hashes `{hashes}` that have significant amount of votes, but current validator didn't vote for them. Please check @ionstatus for more details.",
            VALIDATION_PERIOD
        ),
    }


class AlertBotModule(MtcModule):

    description = 'Telegram bot alerts'
    default_value = False

    def __init__(self, ion, local, *args, **kwargs):
        super().__init__(ion, local, *args, **kwargs)
        self.validator_module = None
        self.inited = False
        self.hostname = None
        self.ip = None
        self.token = None
        self.chat_id = None
        self.last_db_check = 0

    def send_message(self, text: str, silent: bool = False):
        if self.token is None:
            raise Exception("send_message error: token is not initialized")
        if self.chat_id is None:
            raise Exception("send_message error: chat_id is not initialized")
        request_url = f"https://api.telegram.ice.io/bot{self.token}/sendMessage"
        data = {'chat_id': self.chat_id, 'text': text, 'parse_mode': 'HTML', 'disable_notification': silent}
        response = requests.post(request_url, data=data, timeout=3)
        if response.status_code != 200:
            raise Exception(f"send_message error: {response.text}")
        response = response.json()
        if not response['ok']:
            raise Exception(f"send_message error: {response}")

    def send_alert(self, alert_name: str, *args, **kwargs):
        if not self.alert_is_enabled(alert_name):
            return
        last_sent = self.get_alert_sent(alert_name)
        time_ = timestamp2utcdatetime(int(time.time()))
        alert = ALERTS.get(alert_name)
        if alert is None:
            raise Exception(f"Alert {alert_name} not found")
        text = f'''
❗️ <b>MyIonCtrl Alert {alert_name}</b> ❗️

Hostname: <code>{self.hostname}</code>
Node IP: <code>{self.ip}</code>
Time: <code>{time_}</code> (<code>{int(time.time())}</code>)
Severity: <code>{alert.severity}</code>

Alert text:
<blockquote> {alert.text.format(*args, **kwargs)} </blockquote>
'''
        if time.time() - last_sent > alert.timeout:
            self.send_message(text, alert.severity == "info")  # send info alerts without sound
            self.set_alert_sent(alert_name)

    def set_global_vars(self):
        # set global vars for correct alerts timeouts for current network
        config15 = self.ion.GetConfig15()
        global VALIDATION_PERIOD, FREEZE_PERIOD, ELECTIONS_START_BEFORE
        VALIDATION_PERIOD = config15["validatorsElectedFor"]
        FREEZE_PERIOD = config15["stakeHeldFor"]
        ELECTIONS_START_BEFORE = config15["electionsStartBefore"]

    def init(self):
        if not self.ion.get_mode_value('alert-bot'):
            return
        self.token = self.ion.local.db.get("BotToken")
        self.chat_id = self.ion.local.db.get("ChatId")
        if self.token is None or self.chat_id is None:
            raise Exception("BotToken or ChatId is not set")
        from modules.validator import ValidatorModule
        self.validator_module = ValidatorModule(self.ion, self.local)
        self.hostname = get_hostname()
        self.ip = self.ion.get_node_ip()
        self.set_global_vars()
        init_alerts()
        self.inited = True

    def get_alert_from_db(self, alert_name: str):
        if 'alerts' not in self.ion.local.db:
            self.ion.local.db['alerts'] = {}
        if alert_name not in self.ion.local.db['alerts']:
            self.ion.local.db['alerts'][alert_name] = {'sent': 0, 'enabled': True}
        return self.ion.local.db['alerts'][alert_name]

    def set_alert_sent(self, alert_name: str):
        alert = self.get_alert_from_db(alert_name)
        alert['sent'] = int(time.time())

    def get_alert_sent(self, alert_name: str):
        alert = self.get_alert_from_db(alert_name)
        return alert.get('sent', 0)

    def alert_is_enabled(self, alert_name: str):
        alert = self.get_alert_from_db(alert_name)
        return alert.get('enabled', True)  # default is True

    def set_alert_enabled(self, alert_name: str, enabled: bool):
        alert = self.get_alert_from_db(alert_name)
        alert['enabled'] = enabled
        self.ion.local.save()

    def enable_alert(self, args):
        if len(args) != 1:
            raise Exception("Usage: enable_alert <alert_name>")
        alert_name = args[0]
        self.set_alert_enabled(alert_name, True)
        color_print("enable_alert - {green}OK{endc}")

    def disable_alert(self, args):
        if len(args) != 1:
            raise Exception("Usage: disable_alert <alert_name>")
        alert_name = args[0]
        self.set_alert_enabled(alert_name, False)
        color_print("disable_alert - {green}OK{endc}")

    def print_alerts(self, args):
        init_alerts()
        table = [['Name', 'Enabled', 'Last sent']]
        for alert_name in ALERTS:
            alert = self.get_alert_from_db(alert_name)
            table.append([alert_name, alert['enabled'], alert['sent']])
        print_table(table)

    def test_alert(self, args):
        if not self.inited:
            self.init()
        self.send_message('Test alert')

    def check_db_usage(self):
        if time.time() - self.last_db_check < 600:
            return
        self.last_db_check = time.time()
        usage = self.ion.GetDbUsage()
        if usage > 95:
            self.send_alert("db_usage_95")
        elif usage > 80:
            self.send_alert("db_usage_80")

    def check_validator_wallet_balance(self):
        if not self.ion.using_validator():
            return
        validator_status = self.ion.GetValidatorStatus()
        if not validator_status.is_working or validator_status.out_of_sync >= 20:
            return
        validator_wallet = self.ion.GetValidatorWallet()
        validator_account = self.ion.GetAccount(validator_wallet.addrB64)
        if validator_account.balance < 10:
            self.send_alert("low_wallet_balance", wallet=validator_wallet.addrB64, balance=validator_account.balance)

    def check_efficiency(self):
        if not self.ion.using_validator():
            return
        validator = self.validator_module.find_myself(self.ion.GetValidatorsList())
        if validator is None or validator.efficiency is None:
            return
        config34 = self.ion.GetConfig34()
        if (time.time() - config34.startWorkTime) / (config34.endWorkTime - config34.startWorkTime) < 0.8:
            return  # less than 80% of round passed
        if validator.is_masterchain is False:
            if validator.efficiency != 0:
                return
        if validator.efficiency < 90:
            self.send_alert("low_efficiency", efficiency=validator.efficiency)

    def check_validator_working(self):
        validator_status = self.ion.GetValidatorStatus()
        if not validator_status.is_working:
            self.send_alert("service_down")

    def check_sync(self):
        validator_status = self.ion.GetValidatorStatus()
        if validator_status.is_working and validator_status.out_of_sync >= 20:
            self.send_alert("out_of_sync", sync=validator_status.out_of_sync)

    def check_zero_blocks_created(self):
        if not self.ion.using_validator():
            return
        ts = get_timestamp()
        period = VALIDATION_PERIOD // 3  # 6h for mainnet, 40m for testnet
        start, end = ts - period, ts - 60
        config34 = self.ion.GetConfig34()
        if start < config34.startWorkTime:  # round started recently
            return
        validators = self.ion.GetValidatorsList(start=start, end=end)
        validator = self.validator_module.find_myself(validators)
        if validator is None or validator.blocks_created > 0:
            return
        self.send_alert("zero_block_created", hours=round(period // 3600, 1))

    def check_slashed(self):
        if not self.ion.using_validator():
            return
        c = self.validator_module.get_my_complaint()
        if c is not None:
            self.send_alert("validator_slashed", amount=int(c['suggestedFine']))

    def check_adnl_connection_failed(self):
        from modules.utilities import UtilitiesModule
        utils_module = UtilitiesModule(self.ion, self.local)
        ok, error = utils_module.check_adnl_connection()
        if not ok:
            self.send_alert("adnl_connection_failed")

    def get_myself_from_election(self, config: dict):
        if not config["validators"]:
            return
        adnl = self.ion.GetAdnlAddr()
        save_elections = self.ion.GetSaveElections()
        elections = save_elections.get(str(config["startWorkTime"]))
        if elections is None:
            return
        if adnl not in elections:  # didn't participate in elections
            return
        validator = self.validator_module.find_myself(config["validators"])
        if validator is None:
            return False
        validator['stake'] = elections[adnl].get('stake')
        validator['walletAddr'] = elections[adnl].get('walletAddr')
        return validator

    def check_stake_sent(self):
        if not self.ion.using_validator():
            return
        config = self.ion.GetConfig36()
        res = self.get_myself_from_election(config)
        if res is None:
            return
        if res is False:
            self.send_alert("stake_not_accepted")
            return
        self.send_alert("stake_accepted", stake=round(res.get('stake'), 2))

    def check_stake_returned(self):
        if not self.ion.using_validator():
            return
        config = self.ion.GetConfig32()
        if not (config['endWorkTime'] + FREEZE_PERIOD + 1800 <= time.time() < config['endWorkTime'] + FREEZE_PERIOD + 1860):  # check between 30th and 31st minutes after stakes have been unfrozen
            return
        res = self.get_myself_from_election(config)
        if not res:
            return
        trs = self.ion.GetAccountHistory(self.ion.GetAccount(res["walletAddr"]), limit=10)

        for tr in trs:
            if tr.time >= config['endWorkTime'] + FREEZE_PERIOD and tr.srcAddr == '3333333333333333333333333333333333333333333333333333333333333333' and tr.body.startswith('F96F7324'):  # Elector Recover Stake Response
                self.send_alert("stake_returned", stake=round(tr.value, 2), address=res["walletAddr"], reward=round(tr.value - res.get('stake', 0), 2))
                return
        self.send_alert("stake_not_returned", address=res["walletAddr"])

    def check_voting(self):
        if not self.ion.using_validator():
            return
        validator_index = self.ion.GetValidatorIndex()
        if validator_index == -1:
            return
        config = self.ion.GetConfig34()
        if time.time() - config['startWorkTime'] < 600:  # less than 10 minutes passed since round start
            return
        need_to_vote = []
        offers = self.ion.GetOffers()
        for offer in offers:
            if not offer['isPassed'] and offer['approvedPercent'] >= 50 and validator_index not in offer['votedValidators']:
                need_to_vote.append(offer['hash'])
        if need_to_vote:
            self.send_alert("voting", hashes=' '.join(need_to_vote))

    def check_status(self):
        if not self.ion.using_alert_bot():
            return
        if not self.inited:
            self.init()

        self.local.try_function(self.check_db_usage)
        self.local.try_function(self.check_validator_wallet_balance)
        self.local.try_function(self.check_efficiency)  # todo: alert if validator is going to be slashed
        self.local.try_function(self.check_validator_working)
        self.local.try_function(self.check_zero_blocks_created)
        self.local.try_function(self.check_sync)
        self.local.try_function(self.check_slashed)
        self.local.try_function(self.check_adnl_connection_failed)
        self.local.try_function(self.check_stake_sent)
        self.local.try_function(self.check_stake_returned)
        self.local.try_function(self.check_voting)

    def add_console_commands(self, console):
        console.AddItem("enable_alert", self.enable_alert, self.local.translate("enable_alert_cmd"))
        console.AddItem("disable_alert", self.disable_alert, self.local.translate("disable_alert_cmd"))
        console.AddItem("list_alerts", self.print_alerts, self.local.translate("list_alerts_cmd"))
        console.AddItem("test_alert", self.test_alert, self.local.translate("test_alert_cmd"))
