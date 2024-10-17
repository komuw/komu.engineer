package main

import (
	"context"
	stdLog "log"
	"net/http"
	"os"
	"strings"

	"github.com/komuw/ong/config"
	"github.com/komuw/ong/log"
	"github.com/komuw/ong/mux"
	"github.com/komuw/ong/server"
)

// The main func should be very small in size since you cannot test it.
func main() {
	if err := run(); err != nil {
		stdLog.Fatalf("run failed: %#+v", err)
	}
}

func run() error {
	l := log.New(context.Background(), os.Stdout, 30).With("pid", os.Getpid())
	opts := config.DevOpts(l, "Cool989@LimaTena")
	return server.Run(getMux(opts), opts)
}

func getMux(opts config.Opts) mux.Muxer {
	allRoutes := []mux.Route{
		mux.NewRoute("/blog/:file", mux.MethodGet, ServeFileSources()),
	}

	mux := mux.New(
		opts,
		// TODO: add a notFoundHandler
		nil,
		allRoutes...,
	)

	return mux
}

func ServeFileSources() http.HandlerFunc {
	// curl -vL https://localhost:65081/some-place/some-file.png
	cwd, err := os.Getwd()
	if err != nil {
		panic(err)
	}
	cwd = strings.TrimSuffix(cwd, "blogs")
	fs := http.FileServer(http.Dir(cwd))
	realHandler := http.StripPrefix("/blogs/", fs).ServeHTTP

	return func(w http.ResponseWriter, r *http.Request) {
		realHandler(w, r)
	}
}
