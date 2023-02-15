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
      -keyout confs/rootCA.key \
      -out confs/rootCA.crt
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
      -addext "subjectAltName=DNS:example.com,DNS:example.net,DNS:otel_collector,DNS:localhost" \
      -CA confs/rootCA.crt \
      -CAkey confs/rootCA.key  \
      -keyout confs/server.key \
      -out confs/server.crt
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
      -addext "subjectAltName=DNS:example.com,DNS:example.net,DNS:otel_collector,DNS:localhost" \
      -CA confs/rootCA.crt \
      -CAkey confs/rootCA.key  \
      -keyout confs/client.key \
      -out confs/client.crt
  }

  { # clean
    rm -rf confs/*.csr
    rm -rf confs/*.srl

    chmod 666 confs/server.crt confs/server.key confs/rootCA.crt
  }
}
setup_certs