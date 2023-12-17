cd /home/dietm/SmartHub
su -s /bin/bash -c "/usr/local/bin/pip3.11 install -r ./requirements.txt" dietm
su -s /bin/bash -c "/usr/local/bin/python3.11  /home/dietm/SmartHub/smarthub.py > startup.log 2> err.log" dietm
