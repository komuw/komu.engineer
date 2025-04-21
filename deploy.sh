#!/usr/bin/env bash
if test "$BASH" = "" || "$BASH" -uc "a=();true \"\${a[@]}\"" 2>/dev/null; then
    # Bash 4.4, Zsh
    set -xeo pipefail
else
    # Bash 4.3 and older chokes on empty arrays with set -u.
    set -xeo pipefail
fi
shopt -s nullglob globstar

# lint: shellcheck --color=always --shell=bash deploy.sh


# run as:
# export HOST_NAME_IS=SomeIP && bash deploy.sh
#


run_check_env() {
    printf "\n\n running check environment variables: \n"

    if [[ -z "${HOST_NAME_IS}" ]]
    then
        printf "\n\n environment var HOST_NAME_IS is empty \n"
        exit 1
    fi
}

SERVER_IP="${HOST_NAME_IS}"
get_ip() {
    printf "\n\n SERVER_IP are:\n"
        printf "%s\n" "$SERVER_IP"
} 

run_tests(){
    printf "\n\n running tests: \n"

    CWD=$(basename "$PWD")
    if [ "$CWD" == "komu.engineer" ]; then
        #
        echo -n ""
    else
        printf "\n\t You are in the wrong directory $PWD \n"
        exit 1
    fi

    goimports -w . && \
    gofumpt -extra -w . && \
    gofmt -w -s . && \
    go mod tidy && \
    export CGO_ENABLED=1 && \
    go test -race ./... && \
    go vet -all ./... && \
    staticcheck -tests ./... && \
    export CGO_ENABLED=0

    if [[ `git status --porcelain` ]]; then
      # Changes
      printf "\n\t you have uncommited git changes\n"
      exit 1
    else
      # No changes
      echo -n ''
    fi
}

run_build() {
    printf "\n\n build for release: \n"
	rm -rf komu_engineer_website && \
    # build static binary.
    export CGO_ENABLED=0 && \
    go build -trimpath -ldflags="-extldflags=-static" -o komu_engineer_website . && \
    chmod +x komu_engineer_website
}

security_update() {
    printf "\n\n security_update: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    ssh root@"${IP}" \
"set -x;
sudo update-ca-certificates --fresh

sudo apt --fix-broken install -y;
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:jgmath2000/et
sudo apt -y update
# This version of sqlite has a bug to do with interaction between STRICT and REAL values.
# Unfortunately this version(v3.37.2) is the latest in ubuntu sources.
# https://sqlite.org/forum/info/96da0cd6dd291394
sudo apt install -y et sqlite3 net-tools psmisc

sudo apt-get -y dist-upgrade # security updates
sudo apt --fix-broken install -y
sudo apt -y autoremove
sudo apt -y clean
sudo apt -y purge '~c' # https://askubuntu.com/a/181965"
}

run_rsync() {
    printf "\n\n rsync komu_engineer_website build: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    CWD=$(basename "$PWD")
    if [ "$CWD" == "komu.engineer" ]; then
        #
        echo -n ""
    else
        printf "\n\t You are in the wrong directory $PWD \n"
        exit 1
    fi

    NOW=$(date +%dd-%mm-%Yy-%Hh-%Mmin-%Ssec);
    ssh root@"${IP}" \
'mkdir -p /root/serve/komu_engineer_website;'

	rsync -v --recursive \
	  --perms \
	  --executability \
	  komu_engineer_website \
	  root@"${IP}":/root/serve/komu_engineer_website/komu_engineer_website

    rsync -v --recursive \
	  --perms \
	  --executability \
      --exclude .git/ \
      --exclude .gitignore \
	  . \
	  root@"${IP}":/root/serve/komu_engineer_website/
}

install_software(){
    printf "\n\n install_software: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    ssh root@"${IP}" \
'set -x;
cd /root/serve/komu_engineer_website/;
pwd;ls -lsha;

# todo: backup srs sqlite db: https://github.com/komuw/komu.engineer/issues/34

cp /root/serve/komu_engineer_website/komu_engineer_website.service /etc/systemd/system/komu_engineer_website.service
chmod 0777 /etc/systemd/system/komu_engineer_website.service
systemctl daemon-reload
systemctl enable komu_engineer_website.service
systemctl list-unit-files | grep enabled | grep -i komu_engineer_website

cp /root/serve/komu_engineer_website/komu_engineer_website_envs.txt /tmp/komu_engineer_website_envs.txt
echo KOMU_ENGINEER_WEBSITE_SECRET_KEY=$(uuidgen) >> /tmp/komu_engineer_website_envs.txt
cat /tmp/komu_engineer_website_envs.txt
# NB: when the /tmp directory is cleaned up. systemd will be unable to re-start due to missing /tmp/komu_engineer_website_envs.txt

systemctl restart komu_engineer_website
journalctl -xe -n20 --no-pager -u komu_engineer_website'
}

# Note you need to enable ipv6 via:
# https://docs.digitalocean.com/products/networking/ipv6/how-to/enable/#during-creation
# Both the following should work;
#  mtr -r -w --show-ips -4 komu.engineer
#  mtr -r -w --show-ips -6 komu.engineer
main() {
    run_check_env
    get_ip
    run_tests
    run_build
    security_update "$SERVER_IP"
    run_rsync "$SERVER_IP"
    install_software "$SERVER_IP"
}

main
