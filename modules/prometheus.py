from modules.module import MtcModule
import dataclasses
import requests


@dataclasses.dataclass
class Metric:
    name: str
    description: str
    type: str

    def to_format(self, value):
        return f"""
# HELP {self.name} {self.description}
# TYPE {self.name} {self.type}
{self.name} {value}
"""


METRICS = {
    'master_out_of_sync': Metric('validator_masterchain_out_of_sync_seconds', 'Time difference between current time and timestamp of the last known block', 'gauge'),
    'shard_out_of_sync': Metric('validator_shardchain_out_of_sync_blocks', 'Number of blocks node\'s shardclient is behind the last known block', 'gauge'),
    'out_of_ser': Metric('validator_out_of_serialization', 'Number of blocks last state serialization was ago', 'gauge'),
    'vc_up': Metric('validator_console_up', 'Is `validator-console` up', 'gauge'),
    'validator_id': Metric('validator_index', 'Validator index', 'gauge'),
    'stake': Metric('validator_stake', 'Validator stake', 'gauge'),
    'celldb_gc_block': Metric('validator_celldb_gc_block', 'Celldb GC block latency', 'gauge'),
    'celldb_gc_state': Metric('validator_celldb_gc_state', 'Celldb GC queue size', 'gauge'),
}


class PrometheusModule(MtcModule):

    description = 'Prometheus format data exporter'
    default_value = False

    def __init__(self, ton, local, *args, **kwargs):
        super().__init__(ton, local, *args, **kwargs)

    def get_validator_status_metrics(self, result: list):
        status = self.ton.GetValidatorStatus()
        is_working = status.is_working or (status.unixtime is not None)
        if status.masterchain_out_of_sync is not None:
            result.append(METRICS['master_out_of_sync'].to_format(status.masterchain_out_of_sync))
        if status.shardchain_out_of_sync is not None:
            result.append(METRICS['shard_out_of_sync'].to_format(status.shardchain_out_of_sync))
        if status.masterchain_out_of_ser is not None and status.stateserializermasterchainseqno != 0:
            result.append(METRICS['out_of_ser'].to_format(status.masterchain_out_of_ser))
        if status.masterchainblock is not None and status.gcmasterchainblock is not None:
            result.append(METRICS['celldb_gc_block'].to_format(status.masterchainblock - status.gcmasterchainblock))
        if status.gcmasterchainblock is not None and status.last_deleted_mc_state is not None:
            if status.last_deleted_mc_state != 0:
                result.append(METRICS['celldb_gc_state'].to_format(status.gcmasterchainblock - status.last_deleted_mc_state))
            else:
                result.append(METRICS['celldb_gc_state'].to_format(-1))
        result.append(METRICS['vc_up'].to_format(int(is_working)))

    def get_validator_validation_metrics(self, result: list):
        index = self.ton.GetValidatorIndex()
        result.append(METRICS['validator_id'].to_format(index))
        config = self.ton.GetConfig34()
        save_elections = self.ton.GetSaveElections()
        elections = save_elections.get(str(config["startWorkTime"]))
        if elections is not None:
            adnl = self.ton.GetAdnlAddr()
            stake = elections.get(adnl, {}).get('stake')
            if stake:
                result.append(METRICS['stake'].to_format(round(stake, 2)))

    def push_metrics(self):
        if not self.ton.using_prometheus():
            return

        url = self.ton.local.db.get('prometheus_url')
        if url is None:
            raise Exception('Prometheus url is not set')
        metrics = []
        self.local.try_function(self.get_validator_status_metrics, args=[metrics])
        self.local.try_function(self.get_validator_validation_metrics, args=[metrics])
        requests.post(url, data='\n'.join(metrics).encode())

    def add_console_commands(self, console):
        ...
