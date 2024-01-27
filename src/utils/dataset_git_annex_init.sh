#!/bin/bash

source ./lib/log.sh

# Program's help.
function help() {
    cat << EOF
Usage: $0.sh DIR

Initialize a git-annex repository in the existing but empty DIR.
EOF
    exit 0
}

# If nothing is provided, show help and exit.
if [[ $# -lt 1 ]]; then
    help
fi

# Get arguments.
DIR="$1"

# Safety-guards.
if [[ ! -d "$DIR" ]]; then
    log_error "$DIR doesn't exist!"
    exit 1
elif [[ -d "$DIR/.git" ]]; then
    log_error "A git repository is already initialized!"
    exit 1
fi

# Every barriers passed, create the git(-annex) repository.
cd "$DIR"
git init
# Initialize git-annex using the hostname as description.
git annex init "dataset on $(hostname)"
# Use hard links for unlocked files.
git config annex.thin true
# Do not compute checksums.
git config annex.backend WORM
# Increase index performance.
git update-index --index-version 4
GIT_INDEX_FILE=.git/annex/index git update-index --index-version 4
# Don't fullfil the disk.
git config annex.diskreserve "10 gb"
# Fix merging a lot of files.
git config merge.renamelimit 999999
# Disable warning.
git config annex.adviceNoSshCaching false
# Do not lock files.
git annex config --set annex.addunlocked true
# Do not add dotfiles to .git by default.
git annex config --set annex.dotfiles true
# Add files under 1 MB to .git, above to .git/annex.
git annex config --set annex.largefiles 'largerthan=1mb'
