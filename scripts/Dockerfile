FROM ubuntu:24.04 AS builder
RUN apt update
RUN apt install -y wget python3 python3-pip ccache git systemd
ENV BRANCH=feature/fix-installation-scripts
ENV CONFIG="https://cdn.ice.io/testnet/global.config.json"
ENV user=root

RUN wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/refs/heads/$BRANCH/scripts/install.sh
RUN wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/refs/heads/$BRANCH/scripts/ion_installer.sh -O /tmp/ion_installer.sh
RUN bash /tmp/ion_installer.sh -c $CONFIG -v master
RUN chmod +x /install.sh
CMD ["bash", "-c", "/install.sh -m validator -t -i -b $BRANCH -n testnet"]
