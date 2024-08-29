from mypylib.mypylib import color_print
from modules.module import MtcModule


class ValidatorModule(MtcModule):

    description = ('Validator functions. Activates participating in elections and staking. '
                   'If pools and l/s modes are disabled stakes from validator wallet.')

    default_value = True

    def vote_offer(self, args):
        if len(args) == 0:
            color_print("{red}Bad args. Usage:{endc} vo <offer-hash>")
            return
        for offerHash in args:
            self.ion.VoteOffer(offerHash)
        color_print("VoteOffer - {green}OK{endc}")

    def vote_election_entry(self, args):
        from myioncore.functions import Elections
        Elections(self.ion.local, self.ion)
        color_print("VoteElectionEntry - {green}OK{endc}")

    def vote_complaint(self, args):
        try:
            election_id = args[0]
            complaint_hash = args[1]
        except:
            color_print("{red}Bad args. Usage:{endc} vc <election-id> <complaint-hash>")
            return
        self.ion.VoteComplaint(election_id, complaint_hash)
        color_print("VoteComplaint - {green}OK{endc}")

    def add_console_commands(self, console):
        console.AddItem("vo", self.vote_offer, self.local.translate("vo_cmd"))
        console.AddItem("ve", self.vote_election_entry, self.local.translate("ve_cmd"))
        console.AddItem("vc", self.vote_complaint, self.local.translate("vc_cmd"))
