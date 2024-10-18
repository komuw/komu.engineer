package main

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"github.com/komuw/ong/log"
	"go.akshayshah.org/attest"
)

func TestMux(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	mx := getMux(log.New(context.Background(), w, 10), cwd)

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

			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, tt.path, nil)
			mx.ServeHTTP(rec, req)

			res := rec.Result()
			defer res.Body.Close()

			attest.Equal(t, res.StatusCode, tt.expectedStatusCode)
		})
	}
}

func TestMuxRedirects(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	mx := getMux(log.New(context.Background(), w, 10), cwd)

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
			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, v, nil)
			mx.ServeHTTP(rec, req)

			res := rec.Result()
			defer res.Body.Close()
			attest.Equal(t, res.StatusCode, http.StatusMovedPermanently)
		}
	})
}

func TestMuxRouteSubdomains(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)

	w := os.Stderr
	mx := getMux(log.New(context.Background(), w, 10), cwd)

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
			host:               "srs.komu.engineer:80",
			expectedStatusCode: http.StatusOK,
			expectedBody:       "this is the srs subdomain",
		},
		{
			host:               "algo.komu.engineer:80",
			expectedStatusCode: http.StatusOK,
			expectedBody:       "4_stack_n_queue",
		},
	}

	for _, tt := range tests {
		tt := tt

		t.Run(tt.host, func(t *testing.T) {
			t.Parallel()

			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, "/index.html", nil)
			req.Header.Set("Host", tt.host)
			req.Host = tt.host

			mx.ServeHTTP(rec, req)

			res := rec.Result()
			defer res.Body.Close()
			rb, err := io.ReadAll(res.Body)
			attest.Ok(t, err)

			attest.Equal(t, res.StatusCode, tt.expectedStatusCode)
			attest.Subsequence(t, string(rb), tt.expectedBody)
		})
	}
}
