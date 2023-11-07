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

# Sleep to:
# 1. Prevent boot loop in case of programmer's error.
# 2. Wait enough time for J-Link OB be recognize by nrfjprog.
sleep 60

# Start tmux server.
# NOTE: Specifying shell is important, otherwise, it will use "sh" as default
# shell for new windows and panes.
SHELL=/bin/zsh tmux start-server

# Source the project environment and start the collection inside a tmux session.
# NOTE: -d is important to not trying to attach to current terminal, as cron
# doesn't provide terminal.
tmux new-session -d -s collect "tmux set-window-option remain-on-exit on && cd /home/drac/git/screaming_channels_ble/src && direnv exec . ./collect.sh -l INFO -r -y"
