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
	"github.com/komuw/ong/id"
	"github.com/komuw/ong/log"
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
	opts := config.DevOpts(l, id.New())
	opts.DrainTimeout = 1 * time.Nanosecond

	cwd, err := os.Getwd()
	if err != nil {
		return err
	}

	return server.Run(getMux(cwd), opts)
}

func getMux(cwd string) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /", ServeFileSources(cwd))
	mux.HandleFunc("GET /blogs/", ServeFileSources(filepath.Join(cwd, "blogs")))

	{ // redirects.
		mux.HandleFunc("GET /blogs/go-gc-maps", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/01/go-gc-maps", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/consensus", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/02/consensus", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/python-lambda", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/03/python-lambda", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/go-modules-early-peek", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/04/go-modules-early-peek", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/lambda-shim/lambda-shim", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/05/lambda-shim", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/timeScaleDB/timescaleDB-for-logs", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/06/timescaleDB-for-logs", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/celery-clone/understand-how-celery-works", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/07/understand-how-celery-works", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/golang-stackTrace/golang-stackTrace", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/08/golang-stackTrace", http.StatusMovedPermanently)
		})
		mux.HandleFunc("GET /blogs/log-without-losing-context/log-without-losing-context", func(w http.ResponseWriter, r *http.Request) {
			http.Redirect(w, r, "/blogs/09/log-without-losing-context", http.StatusMovedPermanently)
		})
	}

	return mux
}

func ServeFileSources(rootDir string) http.HandlerFunc {
	// curl -vL https://localhost:65081/blogs/ala.txt
	// curl -vL https://localhost:65081/blogs/01/go-gc-maps.html

	if len(rootDir) < 1 {
		panic("rootDir cannot be empty")
	}
	h := fileHandler{rootDir: rootDir}

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
	if err1 == nil {
		defer fl.Close()
	} else {
		fl2, err2 := os.Open(file + ".html")
		fl = fl2
		if err2 != nil {
			e := errors.Join(err1, err2)
			// TODO: log.
			fmt.Println("errrr: ", e)
			http.Error(w, "unable to open file: "+file, http.StatusNotFound)
			return
		}
	}

	fi, err := fl.Stat()
	if err != nil {
		// TODO: log.
		http.Error(w, "unable to stat file: "+file, http.StatusInternalServerError)
		return
	}

	fmt.Println("dirrr: ", fi.IsDir())
	if fi.IsDir() {
		file = filepath.Join(file, "index.html")
		fl3, err3 := os.Open(file)
		fl = fl3
		if err3 != nil {
			// TODO: log.
			fmt.Println("err3: ", err3)
			http.Error(w, "unable to open file: "+file, http.StatusNotFound)
			return
		}

		fi2, err := fl.Stat()
		if err != nil {
			// TODO: log.
			http.Error(w, "unable to stat file: "+file, http.StatusInternalServerError)
			return
		}
		fi = fi2
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
