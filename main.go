package main

import (
	"context"
	"fmt"
	"io"
	stdLog "log"
	"log/slog"
	"mime"
	"net"
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
	opts, l, err := cfg()
	if err != nil {
		return err
	}

	cwd, err := os.Getwd()
	if err != nil {
		return err
	}

	// mx := getMux(l, cwd)
	mx := getMux2(l, opts, cwd)

	return server.Run(mx, opts)
}

func cfg() (config.Opts, *slog.Logger, error) {
	const envVar = "KOMU_ENGINEER_WEBSITE_ENVIRONMENT"
	env := os.Getenv(envVar)

	l := log.New(context.Background(), os.Stdout, 30).With("pid", os.Getpid())
	opts := config.Opts{}

	switch v := env; {
	default:
		return opts, l, errors.Errorf("the env var %s is either not set or has the wrong value. got = `%s`", envVar, v)
	case v == "development":
		opts = config.DevOpts(l, id.New())
		opts.DrainTimeout = 1 * time.Nanosecond
	case v == "production":
		acmeEmail := os.Getenv("KOMU_ENGINEER_WEBSITE_LETSENCRYPT_EMAIL")
		if acmeEmail == "" {
			return opts, l, errors.Errorf("the env var %s is either not set or has the wrong value. got = `%s`", "KOMU_ENGINEER_WEBSITE_LETSENCRYPT_EMAIL", acmeEmail)
		}
		domain := "*.komu.engineer"
		opts = config.LetsEncryptOpts(
			domain,
			id.New(),
			// TODO: change clientIPstrategy based on our server host.
			config.DirectIpStrategy,
			l,
			acmeEmail,
			[]string{domain},
		)
	}

	return opts, l, nil
}

func getMux(l *slog.Logger, cwd string) *http.ServeMux {
	mux := http.NewServeMux()
	// For how precedence matching works,
	// see: https://go.dev/blog/routing-enhancements#precedence
	mux.HandleFunc("GET /", router(l, cwd))

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

func getMux2(l *slog.Logger, opts config.Opts, cwd string) mux.Muxer {
	allRoutes := []mux.Route{
		mux.NewRoute(
			"/*",
			http.MethodGet,
			router(l, cwd),
		),
	}

	return mux.New(
		opts,
		nil,
		allRoutes...,
	)
}

func router(l *slog.Logger, rootDir string) http.HandlerFunc {
	website := serveFileSources(
		l,
		rootDir,
	)
	srs := func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("this is the srs subdomain"))
	}
	algo := serveFileSources(
		// curl -vkL -H "Host:algo.komu.engineer:80" https://localhost:65081/
		l,
		filepath.Join(rootDir, "/blogs/algos-n-data-structures"),
	)
	redirectMap := map[string]string{
		// key is original url, value is the new location.
		"/blogs/go-gc-maps":                                            "/blogs/01/go-gc-maps",
		"/blogs/consensus":                                             "/blogs/02/consensus",
		"/blogs/python-lambda":                                         "/blogs/03/python-lambda",
		"/blogs/go-modules-early-peek":                                 "/blogs/04/go-modules-early-peek",
		"/blogs/lambda-shim/lambda-shim":                               "/blogs/05/lambda-shim",
		"/blogs/timeScaleDB/timescaleDB-for-logs":                      "/blogs/06/timescaleDB-for-logs",
		"/blogs/celery-clone/understand-how-celery-works":              "/blogs/07/understand-how-celery-works",
		"/blogs/golang-stackTrace/golang-stackTrace":                   "/blogs/08/golang-stackTrace",
		"/blogs/log-without-losing-context/log-without-losing-context": "/blogs/09/log-without-losing-context",
	}

	return func(w http.ResponseWriter, r *http.Request) {
		host := r.Host
		args := []any{
			"func", "router",
			"url", r.URL.String(),
			"host", host,
			"r.URL.Path", r.URL.Path,
		}

		{ // handle redirects
			for k, v := range redirectMap {
				if r.URL.Path == k {
					http.Redirect(w, r, v, http.StatusMovedPermanently)
				}
			}
		}

		hst, port, err := net.SplitHostPort(host)
		args = append(args, []any{"err", err, "hst", hst, "port", port}...)
		fmt.Println("\t args: ", args)
		if err != nil {
			l.Error("router_handler", args...)
			website(w, r)
			return
		}
		hst = strings.ToLower(hst)

		if hst == "localhost" {
			website(w, r)
			return
		}
		if strings.Contains(hst, "srs.komu.engineer") {
			// TODO: plugin route to srs.
			srs(w, r)
			return
		}
		if strings.Contains(hst, "algo.komu.engineer") {
			algo(w, r)
			return
		}

		website(w, r)
	}
}

func serveFileSources(l *slog.Logger, rootDir string) http.HandlerFunc {
	// curl -vL https://localhost:65081/blogs/ala.txt
	// curl -vL https://localhost:65081/blogs/01/go-gc-maps.html

	if len(rootDir) < 1 {
		panic("rootDir cannot be empty")
	}
	h := fileHandler{rootDir: rootDir, l: l}

	return func(w http.ResponseWriter, r *http.Request) {
		h.ServeHTTP(w, r)
	}
}

type fileHandler struct {
	// rootDir is required so that a malicious user cannot request for `localhost:80/etc/passwd`
	rootDir string
	l       *slog.Logger
}

func (f fileHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
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
	file = path.Clean(file)
	args := []any{
		"url", r.URL.String(),
		"rootDir", f.rootDir,
		"file", file,
	}

	fl, err1 := os.Open(file)
	if err1 == nil {
		defer fl.Close()
	} else {
		fl2, err2 := os.Open(file + ".html")
		fl = fl2
		if err2 != nil {
			e := errors.Join(err1, err2)
			args = append(args, []any{"err", e}...)
			f.l.Error("fileHandler_response", args...)

			http.Error(w, "unable to open file: "+file, http.StatusNotFound)
			return
		}
	}

	fi, err := fl.Stat()
	if err != nil {
		args = append(args, []any{"err", err}...)
		f.l.Error("fileHandler_response", args...)

		http.Error(w, "unable to stat file: "+file, http.StatusInternalServerError)
		return
	}

	if fi.IsDir() {
		file = filepath.Join(file, "index.html")
		fl3, err3 := os.Open(file)
		fl = fl3
		if err3 != nil {
			args = append(args, []any{"err", err3}...)
			f.l.Error("fileHandler_response", args...)

			http.Error(w, "unable to open file: "+file, http.StatusNotFound)
			return
		}

		fi2, err := fl.Stat()
		if err != nil {
			args = append(args, []any{"err", err}...)
			f.l.Error("fileHandler_response", args...)

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
		args = append(args, []any{"err", err}...)
		f.l.Error("fileHandler_response", args...)
	}
}
