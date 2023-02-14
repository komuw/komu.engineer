#!/usr/bin/env bash
shopt -s nullglob globstar
set -x # have bash print command been ran
set -e # fail if any command fails

setup_certs(){
  { # create CA.
    openssl \
      req \
      -new \
      -newkey rsa:4096 \
      -days 1024 \
      -nodes \
      -x509 \
      -subj "/C=US/ST=CA/O=MyOrg/CN=myOrgCA" \
      -keyout confs/tls/rootCA.key \
      -out confs/tls/rootCA.crt
  }

  { # create server certs.
    openssl \
      req \
      -new \
      -newkey rsa:2048 \
      -days 372 \
      -nodes \
      -x509 \
      -subj "/C=US/ST=CA/O=MyOrg/CN=myOrgCA" \
      -addext "subjectAltName=DNS:example.com,DNS:example.net,DNS:otel_collector" \
      -CA confs/tls/rootCA.crt \
      -CAkey confs/tls/rootCA.key  \
      -keyout confs/tls/server.key \
      -out confs/tls/server.crt
  }

  { # create client certs.
    openssl \
      req \
      -new \
      -newkey rsa:2048 \
      -days 372 \
      -nodes \
      -x509 \
      -subj "/C=US/ST=CA/O=MyOrg/CN=myOrgCA" \
      -addext "subjectAltName=DNS:example.com,DNS:example.net,DNS:otel_collector" \
      -CA confs/tls/rootCA.crt \
      -CAkey confs/tls/rootCA.key  \
      -keyout confs/tls/client.key \
      -out confs/tls/client.crt
  }

  { # clean
    rm -rf confs/tls/*.csr
    rm -rf confs/tls/*.srl

    touch confs/otel_file_exporter.json
    chmod 666 confs/otel_file_exporter.json # otel-collector docker image has no writable file-system
    chmod 666 confs/tls/server.crt confs/tls/server.key confs/tls/rootCA.crt
  }
}
setup_certs