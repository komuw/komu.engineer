package main

import (
	"context"
	"fmt"
	"io"
	stdLog "log"
	"mime"
	"net/http"
	"os"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/komuw/ong/config"
	"github.com/komuw/ong/errors"
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
	cwd, err := os.Getwd()
	if err != nil {
		panic(err)
	}

	allRoutes := []mux.Route{
		// mux.NewRoute("/blogs/:file", mux.MethodGet, ServeFileSources()),
		// mux.NewRoute("/blogs/imgs/:file", mux.MethodGet, ServeFileSources()),
		mux.NewRoute("/blogs/10/:file", mux.MethodGet, ServeFileSources(filepath.Join(cwd, "blogs"))),
	}

	mux := mux.New(
		opts,
		// TODO: add a notFoundHandler
		nil,
		allRoutes...,
	)

	return mux
}

func ServeFileSources(rootDir string) http.HandlerFunc {
	// curl -vL https://localhost:65081/blogs/ala.txt
	// curl -vL https://localhost:65081/blogs/01/go-gc-maps.html

	// TODO: remove this.
	h := fileHandler{rootDir: rootDir}
	fs := http.FileServer(http.Dir(rootDir))
	realHandler := http.StripPrefix("/blogs/", fs).ServeHTTP
	_ = realHandler

	return func(w http.ResponseWriter, r *http.Request) {
		fmt.Println("r.URL.String()1: ", r.URL.String())
		h.ServeHTTP(w, r)
	}
}

type fileHandler struct {
	// rootDir is required so that a malicious user cannot request for `localhost:80/etc/passwd`
	rootDir string
}

func (f fileHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	const indexPage = "/index.html" // TODO: handle this.

	// TODO: handle directory. Maybe you should list directory.
	// See stdlib.http.serveFile.dirList

	upath := r.URL.Path
	if !strings.HasPrefix(upath, "/") {
		upath = "/" + upath
	}
	upath = upath[1:] // remove slash
	rootLast := filepath.Base(f.rootDir)
	if strings.HasPrefix(upath, rootLast) {
		upath = "/" + strings.TrimPrefix(upath, rootLast)
	}
	file := filepath.Join(f.rootDir, upath)
	fmt.Println("rootLast: ", rootLast)
	fmt.Println("upath: ", upath)
	fmt.Println("file1: ", file)

	file = path.Clean(file)
	fmt.Println("file2: ", file)
	fl, err1 := os.Open(file)
	if err1 != nil {
		{
			file = file + ".html"
			fl2, err2 := os.Open(file)
			fl = fl2
			if err2 != nil {
				e := errors.Join(err1, err2)
				// TODO: log.
				fmt.Println("errrr: ", e)
				http.Error(w, "unable to open file: "+file, http.StatusInternalServerError)
				return
			}
		}
	}
	defer fl.Close()

	fi, err := fl.Stat()
	if err != nil {
		// TODO: log.
		http.Error(w, "unable to stat file: "+file, http.StatusInternalServerError)
		return
	}

	// If Content-Type isn't set, use the file's extension to find it, but
	// if the Content-Type is unset explicitly, do not sniff the type.
	ctype := ""
	ctypes, haveType := w.Header()["Content-Type"]
	if !haveType {
		ctype = mime.TypeByExtension(filepath.Ext(file))
		if ctype != "" {
			w.Header().Set("Content-Type", ctype)
		}
	} else {
		if len(ctypes) > 0 {
			ctype = ctypes[0]
			w.Header().Set("Content-Type", ctype)
		}
	}
	w.Header().Set("Content-Length", strconv.FormatInt(fi.Size(), 10))

	w.WriteHeader(http.StatusOK)
	if _, err := io.Copy(w, fl); err != nil {
		// TODO: log.
	}
}
