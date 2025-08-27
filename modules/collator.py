from modules.module import MtcModule
from mypylib import color_print, print_table
from mytoncore import b642hex, signed_int_to_hex64, shard_prefix_len, hex_shard_to_int, shard_prefix, shard_is_ancestor
from mytonctrl.utils import pop_arg_from_args


class CollatorModule(MtcModule):

    description = 'Blocks collator-only module.'
    default_value = False


    def add_collator_to_vc(self, adnl_addr: str, shard: str):
        self.local.add_log("start add_collator_to_vc function", "debug")
        result = self.ton.validatorConsole.Run(f"add-collator {adnl_addr} {shard}")
        return result

    @staticmethod
    def _check_input_shards(node_shards: list, shards_need_to_add: list, monitor_min_split: int):
        true_monitoring_shards = []
        for sh in node_shards:
            shard_id = hex_shard_to_int(sh)
            if shard_id['workchain'] == -1:
                continue
            shard = shard_id['shard']
            if shard_prefix_len(shard) > monitor_min_split:
                shard_id['shard'] = shard_prefix(shard, monitor_min_split)
            true_monitoring_shards.append(shard_id)
        for sh in shards_need_to_add:
            shard_id = hex_shard_to_int(sh)
            found = False
            for true_shard in true_monitoring_shards:
                if shard_id['workchain'] == true_shard['workchain'] and \
                        shard_is_ancestor(true_shard['shard'], shard_id['shard']):
                    found = True
                    break
            if not found:
                raise Exception(
                    f'This node already has shards to monitor, '
                    f'but shard {shard_id} is not monitored by the node: {true_monitoring_shards} It\'s highly not recommended to add new shards for node to monitor. '
                    f'If you are sure you want to add new collator use option `--force`.'
                )

    def setup_collator(self, args: list):
        from mytoninstaller.mytoninstaller import set_node_argument
        from mytoninstaller.node_args import get_node_args

        if not args:
            color_print("{red}Bad args. Usage:{endc} setup_collator [--force] [--adnl <ADNL address>] <shard1> [shard2] ...")
            return
        force = '--force' in args
        args.remove('--force') if '--force' in args else None
        adnl_addr = pop_arg_from_args(args, '--adnl')
        shards = args
        node_args = get_node_args()
        if '--add-shard' not in node_args:
            node_args['--add-shard'] = []

        node_shards = node_args['--add-shard']
        shards_need_to_add = [shard for shard in shards if shard not in node_shards]
        if not force and shards_need_to_add and '-M' in node_args:
            monitor_min_split = self.ton.get_basechain_config()['monitor_min_split']
            self._check_input_shards(node_shards, shards_need_to_add, monitor_min_split)
        if adnl_addr is None:
            adnl_addr = self.ton.CreateNewKey()
        self.ton.AddAdnlAddrToValidator(adnl_addr)
        for shard in shards:
            res = self.add_collator_to_vc(adnl_addr, shard)
            if 'successfully' not in res:
                raise Exception(f'Failed to enable collator: add-collator query failed: {res}')
        self.local.add_log(f'Collator added for shards {shards} with ADNL address {adnl_addr}\n'
                           f'Editing monitoring shards.')
        if '-M' not in node_args:
            set_node_argument(self.local, ['-M'])
        if shards_need_to_add:
            set_node_argument(self.local, ['--add-shard', ' '.join(node_args['--add-shard'] + shards_need_to_add)])
        commands_text = [f'`add_collator {adnl_addr} {s}`' for s in shards]
        self.local.add_log(f'Collator enabled for shards {shards}\n'
                           f'To add this collator to validator use command:\n'
                           + '\n'.join(commands_text))
        color_print("setup_collator - {green}OK{endc}")

    def stop_collator(self, args: list):
        if not args:
            text = f"{{red}}WARNING: This action will stop and delete all local collation broadcasts from this node for all shards.{{endc}}\n"
            color_print(text)
            if input("Continue anyway? [Y/n]\n").strip().lower() not in ('y', ''):
                print('aborted.')
                return
            collators = self.get_collators()
            if not collators:
                print("No collators found")
                return
            errors = []
            for c in collators:
                adnl_hex = b642hex(c['adnl_id']).upper()
                workchain = int(c['shard']['workchain'])
                shard_int = int(c['shard']['shard'])
                res = self.ton.validatorConsole.Run(f"del-collator {adnl_hex} {workchain} {shard_int}")
                if 'success' not in res.lower():
                    errors.append(res.strip())
            if errors:
                raise Exception(f"Failed to delete some collators: {'; '.join(errors)}")
            color_print("stop_collator - {green}OK{endc}")
            return

        if len(args) == 2:
            adnl_addr, shard_str = args
            if ':' not in shard_str:
                color_print("{red}Bad args. Usage:{endc} stop_collator <adnl_id> <workchain>:<shard_hex>")
                return
            shard_id = hex_shard_to_int(shard_str)
            workchain = int(shard_id['workchain'])
            shard_int = int(shard_id['shard'])
        else:
            color_print("{red}Bad args. Usage:{endc} stop_collator <adnl_id> <workchain>:<shard_hex>")
            return

        res = self.ton.validatorConsole.Run(f"del-collator {adnl_addr} {workchain} {shard_int}")
        if 'successfully removed collator' not in res.lower():
            raise Exception(f'Failed to disable collator: del-collator query failed: {res}')
        color_print("stop_collator - {green}OK{endc}")

    def get_collators(self):
        return self.ton.GetValidatorConfig()['collators']

    def print_collators(self, args: list = None):
        collators = self.get_collators()
        if not collators:
            print("No collators found")
            return
        print("Collators list:")
        table = [['ADNL Address', 'Shard']]
        for c in collators:
            table.append([b642hex(c['adnl_id']).upper(), f"{c['shard']['workchain']}:{signed_int_to_hex64(int(c['shard']['shard']))}"])
        print_table(table)

    def add_validator_to_collation_wl(self, args: list):
        if len(args) < 1:
            color_print("{red}Bad args. Usage:{endc} add_validator_to_collation_wl <adnl> [adnl2] [adnl3] ...")
            return
        self.ton.validatorConsole.Run(f"collator-whitelist-enable 1")
        self.local.add_log("Collation whitelist enabled")
        for adnl_addr in args:
            result = self.ton.validatorConsole.Run(f"collator-whitelist-add {adnl_addr}")
            if 'success' not in result:
                raise Exception(f'Failed to add validator to collation whitelist: {result}')
        color_print("add_validator_to_collation_wl - {green}OK{endc}")

    def delete_validator_from_collation_wl(self, args: list):
        if len(args) < 1:
            color_print("{red}Bad args. Usage:{endc} delete_validator_from_collation_wl <adnl> [adnl2] [adnl3] ...")
            return
        for adnl_addr in args:
            result = self.ton.validatorConsole.Run(f"collator-whitelist-del {adnl_addr}")
            if 'success' not in result:
                raise Exception(f'Failed to delete validator from collation whitelist: {result}')
        color_print("delete_validator_from_collation_wl - {green}OK{endc}")

    def disable_collation_validator_wl(self, args: list):
        if len(args) != 0:
            color_print("{red}Bad args. Usage:{endc} disable_collation_validator_wl")
            return
        result = self.ton.validatorConsole.Run(f"collator-whitelist-enable 0")
        if 'success' not in result:
            raise Exception(f'Failed to disable collation validator whitelist: {result}')
        color_print("disable_collation_validator_wl - {green}OK{endc}")

    def print_collation_validators_whitelist(self, args: list = None):
        result = self.ton.validatorConsole.Run('collator-whitelist-show')
        result = result.split('conn ready')[1].strip()
        print(result)

    @classmethod
    def check_enable(cls, ton: "MyTonCore"):
        if ton.using_validator():
            raise Exception(f'Cannot enable collator mode while validator mode is enabled. '
                            f'Use `disable_mode validator` first.')

    def check_disable(self):
        if not self.get_collators():
            return
        text = f"{{red}}WARNING: This node probably has active collator working and synchronizes not the whole blockchain, thus it may not work as expected in other node modes. Make sure you know what you're doing.{{endc}}\n"
        color_print(text)
        if input("Continue anyway? [Y/n]\n").strip().lower() not in ('y', ''):
            print('aborted.')
            return

    def add_console_commands(self, console):
        console.AddItem("setup_collator", self.setup_collator, self.local.translate("setup_collator_cmd"))
        console.AddItem("print_local_collators", self.print_collators, self.local.translate("print_local_collators_cmd"))
        console.AddItem("add_validator_to_collation_wl", self.add_validator_to_collation_wl, self.local.translate("add_validator_to_collation_wl_cmd"))
        console.AddItem("delete_validator_from_collation_wl", self.delete_validator_from_collation_wl, self.local.translate("delete_validator_from_collation_wl_cmd"))
        console.AddItem("disable_collation_wl", self.disable_collation_validator_wl, self.local.translate("disable_collation_validator_wl_cmd"))
        console.AddItem("print_collation_whitelist", self.print_collation_validators_whitelist, self.local.translate("print_collation_validators_whitelist_cmd"))
        console.AddItem("stop_collator", self.stop_collator, self.local.translate("stop_collator_cmd"))
