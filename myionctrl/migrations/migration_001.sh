#!/bin/bash

# installing pip package
if [ -f "setup.py" ]; then 
    workdir=$(pwd)
else
    workdir=/usr/src/myionctrl
fi

cd $workdir
pip3 install -U pip .

# update /usr/bin/myionctrl
echo "    Updating /usr/bin/myionctrl"
cat <<EOF > /usr/bin/myionctrl
#!/bin/bash
/usr/bin/python3 -m myionctrl \$@
EOF
chmod +x /usr/bin/myionctrl

# update /etc/systemd/system/myioncore.service
echo "    Updating myioncore service"
sed -i 's\/usr/src/myionctrl/myioncore.py\-m myioncore\g' /etc/systemd/system/myioncore.service
systemctl daemon-reload
