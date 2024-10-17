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
		name string
		path string
	}{
		{
			name: "UnknownUri",
			path: "/UnknownUri",
		},
	}

	for _, tt := range tests {
		tt := tt
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			rec := httptest.NewRecorder()
			req := httptest.NewRequest(http.MethodGet, tt.path, nil)
			mx.ServeHTTP(rec, req)

			res := rec.Result()
			defer res.Body.Close()

			attest.Equal(t, res.StatusCode, http.StatusNotFound)
		})
	}
}
