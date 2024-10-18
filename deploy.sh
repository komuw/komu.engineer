#!/usr/bin/env bash
if test "$BASH" = "" || "$BASH" -uc "a=();true \"\${a[@]}\"" 2>/dev/null; then
    # Bash 4.4, Zsh
    set -eo pipefail
else
    # Bash 4.3 and older chokes on empty arrays with set -u.
    set -eo pipefail
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
	rm -rf website && \
    # build static binary.
    export CGO_ENABLED=0 && \
    go build -trimpath -ldflags="-extldflags=-static" -o website .
    chmod +x website
}

security_update() {
    printf "\n\n security_update: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    ssh root@"${IP}" \
"sudo update-ca-certificates --fresh

sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:jgmath2000/et
sudo apt -y update
# This version of sqlite has a bug to do with interaction between STRICT and REAL values.
# Unfortunately this version(v3.37.2) is the latest in ubuntu sources.
# https://sqlite.org/forum/info/96da0cd6dd291394
sudo apt install -y et sqlite3

sudo apt-get -y dist-upgrade # security updates
sudo apt -y autoremove
sudo apt -y clean
sudo apt -y purge '~c' # https://askubuntu.com/a/181965"
}

run_rsync() {
    printf "\n\n rsync website build: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    NOW=$(date +%dd-%mm-%Yy-%Hh-%Mmin-%Ssec);
    ssh root@"${IP}" \
'mkdir -p /root/serve/;'

	rsync -v --recursive \
	  --perms \
	  --executability \
	  website \
	  root@"${IP}":/root/serve/website
}

install_software(){
    printf "\n\n install_software: \n"

    IP=${1:-NotSet}
    if [ "$IP" == "NotSet"  ]; then
        printf "\n\n IP should not be empty\n"
        exit 1
    fi

    ssh root@"${IP}" \
'cd /root/serve/;
pwd;ls -lsha;
OLD_WEBSITE_PID=$(pidof website);
echo "OLD_WEBSITE_PID = ${OLD_WEBSITE_PID}";
export WEBSITE_ENVIRONMENT=production;
export WEBSITE_LETSENCRYPT_EMAIL=komuw05+komu-engineer-LetsencryptEmail@gmail.com;
rm -rf /tmp/website_background.out;
./website > /tmp/website_background.out 2>&1 &
sleep 5;
NEW_WEBSITE_PID=$(pidof website);
echo "NEW_WEBSITE_PID = ${NEW_WEBSITE_PID}";
kill -15 ${OLD_WEBSITE_PID};
sleep 15;
tail -n10 /tmp/website_background.out;'
}

# Note you need to enable ipv6 via:
# https://docs.digitalocean.com/products/networking/ipv6/how-to/enable/#during-creation
# Both the following should work;
#  mtr -r -w --show-ips -4 dushed.com
#  mtr -r -w --show-ips -6 dushed.com
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
