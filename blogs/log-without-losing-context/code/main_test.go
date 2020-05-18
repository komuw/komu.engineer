package main

import (
	"testing"
)

// run this as;
//   go test -v ./...
func TestWrap(t *testing.T) {
	_, err := atoi()
	if err != nil {
		t.Log(err)

	}
}
