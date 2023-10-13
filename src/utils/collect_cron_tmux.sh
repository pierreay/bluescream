# * About

# To automatically fix some crashes during collection, a strategy is to reboot
# the computer to reset everything. This script is meant to be executed by
# crontab after reboot, spawning the collection script in a tmux session
# attachable by a user.

# * Usage

# Run:
# $ crontab -e
# Put inside:
# @reboot cd /home/drac/git/screaming_channels_ble/src && ./utils/collect_cron_tmux.sh > /tmp/crontab.log 2>&1

# * Script

# Sleep a bit to prevent boot loop in case of code error.
# TODO: Uncomment the following line.
# sleep 30

# Start tmux server.
SHELL=/bin/zsh tmux start-server

# Source the project environment and start the collection inside a tmux session.
# NOTE: -d is important to not trying to attach to current terminal, as cron
# doesn't provide terminal.
tmux new-session -d -s collect "cd /home/drac/git/screaming_channels_ble/src && direnv exec . ./collect.sh"
