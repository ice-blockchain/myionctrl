FROM ubuntu:24.04 AS builder
RUN apt update
RUN apt install -y --no-install-recommends wget python3 python3-pip ccache git \
  systemd systemd-sysv dbus dbus-user-session ca-certificates
ENV BRANCH=feature/fix-installation-scripts
ENV CONFIG="https://cdn.ice.io/testnet/global.config.json"
ENV user=root

# Make journald keep logs in memory (safer in containers)
RUN sed -ri 's/^#?Storage=.*/Storage=volatile/' /etc/systemd/journald.conf

# Mask services/units that are problematic or pointless in containers
RUN for s in \
      getty@.service systemd-logind.service user@.service \
      systemd-remount-fs.service \
      dev-hugepages.mount sys-fs-fuse-connections.mount \
      sys-kernel-config.mount sys-kernel-debug.mount \
    ; do ln -sf /dev/null "/etc/systemd/system/${s}"; done

# Helpful volumes; /run and /tmp should be tmpfs at runtime
VOLUME ["/sys/fs/cgroup"]

RUN wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/refs/heads/$BRANCH/scripts/install.sh
RUN wget https://raw.githubusercontent.com/ice-blockchain/myionctrl/refs/heads/$BRANCH/scripts/ion_installer.sh -O /tmp/ion_installer.sh
RUN bash /tmp/ion_installer.sh -c $CONFIG -v master
RUN chmod +x /install.sh

COPY ./myionctrlinstaller.service /etc/systemd/system

#replace BRANCH_NAME with the actual branch name
RUN sed -i -e "s#BRANCH_NAME#$BRANCH#g" /etc/systemd/system/myionctrlinstaller.service

#install a service which runs the myionctrl install script at startup
RUN systemctl enable myionctrlinstaller.service

CMD ["/sbin/init"]
#CMD ["bash", "-c", "/install.sh -m validator -t -i -b $BRANCH -n testnet"]
