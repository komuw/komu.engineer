package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"go.akshayshah.org/attest"
)

func TestMux(t *testing.T) {
	t.Parallel()

	cwd, err := os.Getwd()
	attest.Ok(t, err)
	fmt.Println("cwd: ", cwd)

	mx := getMux(cwd)

	tests := []struct {
		path               string
		expectedStatusCode int
	}{
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
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.path, func(t *testing.T) {
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
