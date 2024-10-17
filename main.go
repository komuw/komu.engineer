package main

import (
	"context"
	"fmt"
	stdLog "log"
	"net/http"
	"os"
	"path/filepath"
	"time"

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
	opts.DrainTimeout = 1 * time.Nanosecond
	return server.Run(getMux(opts), opts)
}

func getMux(opts config.Opts) mux.Muxer {
	allRoutes := []mux.Route{
		mux.NewRoute("/blogs/:file", mux.MethodGet, ServeFileSources()),
		mux.NewRoute("/blogs/imgs/:file", mux.MethodGet, ServeFileSources()),
		mux.NewRoute("/blogs/01/:file", mux.MethodGet, ServeFileSources()),
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
	// curl -vL https://localhost:65081/blogs/ala.txt
	// curl -vL https://localhost:65081/blogs/01/go-gc-maps.html
	cwd, err := os.Getwd()
	if err != nil {
		panic(err)
	}
	cwd = filepath.Join(cwd, "blogs")
	fs := http.FileServer(http.Dir(cwd))
	realHandler := http.StripPrefix("/blogs/", fs).ServeHTTP

	return func(w http.ResponseWriter, r *http.Request) {
		fmt.Println("cwd: ", cwd)
		fmt.Println("r.URL.String(): ", r.URL.String())
		realHandler(w, r)
	}
}
