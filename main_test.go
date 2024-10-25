package main

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"math"
	"math/rand/v2"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/komuw/ong/config"
	"github.com/komuw/ong/id"
	"github.com/komuw/ong/log"
	"github.com/komuw/ong/mux"
	"github.com/komuw/srs/ext"
	"go.akshayshah.org/attest"
)

// TODO: fix tests.

/////////////////////////////// utils ///////////////////////

func getPort() uint16 {
	r := rand.IntN(10_000) + 1
	p := math.MaxUint16 - uint16(r)
	return p
}

// Taken from https://github.com/komuw/ong/blob/v0.1.11/internal/tst/tst.go#L17-L19
func TlsServer(h http.Handler, domain string, httpsPort uint16) (*httptest.Server, error) {
	if !testing.Testing() {
		panic("this func should only be called from tests")
	}

	ts := httptest.NewUnstartedServer(h)
	if err := ts.Listener.Close(); err != nil {
		return nil, err
	}

	l, err := net.Listen("tcp", net.JoinHostPort(domain, fmt.Sprintf("%d", httpsPort)))
	if err != nil {
		return nil, err
	}

	ts.Listener = l
	ts.StartTLS()

	return ts, nil
}

// Taken from https://github.com/komuw/ong/blob/v0.1.11/internal/tst/tst.go#L83-L84
func Ping(port uint16) error {
	if !testing.Testing() {
		panic("this func should only be called from tests")
	}

	var err error
	count := 0
	maxCount := 12

	for {
		count = count + 1
		time.Sleep(1 * time.Second)
		if _, err := net.DialTimeout("tcp", fmt.Sprintf("localhost:%d", port), 1*time.Second); err == nil {
			fmt.Println("connected to ", port, "after: ", count)
			break
		}

		if count > maxCount {
			err = fmt.Errorf("ping max count(%d) reached: %w", maxCount, err)
			break
		}
	}

	return err
}

/////////////////////////////////////////////////////////////

func TestMux(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	l := log.New(context.Background(), w, 10)
	opts := config.DevOpts(l, id.UUID4().String())
	opts.Domain = "localhost"
	mx := getMux(l, opts, cwd, mux.Muxer{})

	httpsPort := getPort()
	ts, err := TlsServer(mx, opts.Domain, httpsPort)
	attest.Ok(t, err)
	t.Cleanup(func() {
		// It is important that we close in `t.Cleanup` rather than `defer ts.Close()`
		// This is because using defer will close it for this fumc.
		// When we call the server in `t.Run` it will already be closed.
		ts.Close()
	})
	attest.Ok(t, Ping(httpsPort)) // wait for server to start.

	tr := &http.Transport{
		// since we are using self-signed certificates, we need to skip verification.
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr}

	tests := []struct {
		path               string
		expectedStatusCode int
	}{
		{
			path:               "/",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/UnknownUri",
			expectedStatusCode: http.StatusNotFound,
		},
		{
			path:               "/blogs/10/dont-use-a-different-interface-for-testing",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/blogs/10/imgs/mock-test-coverage.png",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/site.css",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/about",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/about.html",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/cv/komu-CV.pdf",
			expectedStatusCode: http.StatusOK,
		},
		{
			path:               "/cv/okay-CV.pdf",
			expectedStatusCode: http.StatusNotFound,
		},
		// TODO: fix this
		// {
		// 	path:               "/blogs",
		// 	expectedStatusCode: http.StatusOK,
		// },
	}

	for _, tt := range tests {
		tt := tt
		t.Run(strings.ReplaceAll(tt.path, "/", ""), func(t *testing.T) {
			t.Parallel()

			url := ts.URL + tt.path
			url = strings.ReplaceAll(url, "127.0.0.1", "localhost")
			res, err := client.Get(url)
			attest.Ok(t, err)
			defer res.Body.Close()

			rb, err := io.ReadAll(res.Body)
			attest.Ok(t, err)
			_ = rb

			attest.Equal(t, res.StatusCode, tt.expectedStatusCode)
		})
	}
}

func TestMuxRedirects(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	l := log.New(context.Background(), w, 10)
	opts := config.DevOpts(l, id.UUID4().String())
	opts.Domain = "localhost"
	mx := getMux(l, opts, cwd, mux.Muxer{})

	httpsPort := getPort()
	ts, err := TlsServer(mx, opts.Domain, httpsPort)
	attest.Ok(t, err)
	t.Cleanup(func() {
		// It is important that we close in `t.Cleanup` rather than `defer ts.Close()`
		// This is because using defer will close it for this fumc.
		// When we call the server in `t.Run` it will already be closed.
		ts.Close()
	})
	attest.Ok(t, Ping(httpsPort)) // wait for server to start.

	tr := &http.Transport{
		// since we are using self-signed certificates, we need to skip verification.
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	clientNoRedirect := &http.Client{
		Transport: tr,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	} // does NOT follow redirects.
	clientWithRedirect := &http.Client{Transport: tr} // follows redirects.

	t.Run("redirects", func(t *testing.T) {
		t.Parallel()

		for _, v := range []string{
			"/blogs/go-gc-maps",
			"/blogs/consensus",
			"/blogs/python-lambda",
			"/blogs/go-modules-early-peek",
			"/blogs/lambda-shim/lambda-shim",
			"/blogs/timeScaleDB/timescaleDB-for-logs",
			"/blogs/celery-clone/understand-how-celery-works",
			"/blogs/golang-stackTrace/golang-stackTrace",
			"/blogs/log-without-losing-context/log-without-losing-context",
		} {
			{
				url := ts.URL + v
				url = strings.ReplaceAll(url, "127.0.0.1", "localhost")
				res, err := clientNoRedirect.Get(url)
				attest.Ok(t, err)
				defer res.Body.Close()

				rb, err := io.ReadAll(res.Body)
				attest.Ok(t, err)
				_ = rb
				attest.Equal(t, res.StatusCode, http.StatusMovedPermanently, attest.Sprintf("url: %v", url))
			}
			{
				url := ts.URL + v
				url = strings.ReplaceAll(url, "127.0.0.1", "localhost")
				res, err := clientWithRedirect.Get(url)
				attest.Ok(t, err)
				defer res.Body.Close()

				rb, err := io.ReadAll(res.Body)
				attest.Ok(t, err)
				_ = rb
				attest.Equal(t, res.StatusCode, http.StatusOK, attest.Sprintf("url: %v", url))
			}
		}
	})
}

func TestMuxRouteSubdomains(t *testing.T) {
	t.Parallel()

	srsMx := func(t *testing.T) mux.Muxer {
		dbPath := t.TempDir() + "/srs.sqlite"
		mx, _, closer, err := ext.Run(dbPath)
		attest.Ok(t, err)
		t.Cleanup(func() {
			closer()
		})

		return mx
	}

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	l := log.New(context.Background(), w, 10)
	opts := config.DevOpts(l, id.UUID4().String())
	opts.Domain = "localhost"
	mx := getMux(l, opts, cwd, srsMx(t))

	httpsPort := getPort()
	ts, err := TlsServer(mx, opts.Domain, httpsPort)
	attest.Ok(t, err)
	t.Cleanup(func() {
		// It is important that we close in `t.Cleanup` rather than `defer ts.Close()`
		// This is because using defer will close it for this fumc.
		// When we call the server in `t.Run` it will already be closed.
		ts.Close()
	})
	attest.Ok(t, Ping(httpsPort)) // wait for server to start.

	tr := &http.Transport{
		// since we are using self-signed certificates, we need to skip verification.
		TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
	}
	client := &http.Client{Transport: tr} // follows redirects.

	tests := []struct {
		host               string
		expectedStatusCode int
		expectedBody       string
	}{
		{
			host:               "localhost:80",
			expectedStatusCode: http.StatusOK,
			expectedBody:       "Is a software developer currently",
		},
		{
			host:               "srs.localhost:80",
			expectedStatusCode: http.StatusOK,
			expectedBody:       "this is the srs subdomain",
		},
		{
			host:               "srs.localhost", // no port
			expectedStatusCode: http.StatusOK,
			expectedBody:       "this is the srs subdomain",
		},
		{
			host:               "algo.localhost:80",
			expectedStatusCode: http.StatusOK,
			expectedBody:       "4_stack_n_queue",
		},
	}

	for _, tt := range tests {
		tt := tt

		t.Run(tt.host, func(t *testing.T) {
			t.Parallel()

			url := ts.URL + "/index.html"
			url = strings.ReplaceAll(url, "127.0.0.1", "localhost")
			req, err := http.NewRequest(http.MethodGet, url, nil)
			attest.Ok(t, err)
			req.Header.Set("Host", tt.host)
			req.Host = tt.host

			res, err := client.Do(req)
			attest.Ok(t, err)
			defer res.Body.Close()

			rb, err := io.ReadAll(res.Body)
			attest.Ok(t, err)
			_ = rb

			attest.Equal(t, res.StatusCode, tt.expectedStatusCode)
			attest.Subsequence(t, string(rb), tt.expectedBody)
		})
	}
}
