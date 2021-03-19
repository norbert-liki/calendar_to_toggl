# Install Stackdriver logging agent
curl -sSO https://dl.google.com/cloudagents/install-logging-agent.sh
sudo bash install-logging-agent.sh

# Install or update needed software
apt-get update
apt-get install -yq git python python-pip
pip install --upgrade pip pipenv

# Account to own server process
useradd -m -d /home/pythonapp pythonapp

# Fetch source code
export HOME=/root
git clone -b ml_pred https://github.com/norbert-liki/calendar_to_toggl.git /opt/app

# Python environment setup
pipenv install --system --deploy
pipenv shell
pip install -r /opt/app/requirements.txt

# Set ownership to newly created account
chown -R pythonapp:pythonapp /opt/app

# Run the training script
python /opt/app/train.py