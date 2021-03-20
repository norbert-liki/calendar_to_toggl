# Install Stackdriver logging agent
curl -sSO https://dl.google.com/cloudagents/install-logging-agent.sh
sudo bash install-logging-agent.sh

# Install or update needed software
apt-get update
apt-get install -yq git python3 python3-pip cmake
pip3 install --upgrade pip pipenv

# Account to own server process
useradd -m -d /home/pythonapp pythonapp

# Fetch source code
export HOME=/root
git clone -b ml_pred https://github.com/norbert-liki/calendar_to_toggl.git /opt/app

# Python environment setup
cd /opt/app
pipenv install --system --deploy
pipenv install pycaret[full]==2.3.0 --skip-lock

# Set ownership to newly created account
chown -R pythonapp:pythonapp /opt/app

# Run the training script
pipenv run python /opt/app/train.py