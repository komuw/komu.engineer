package errors

//
// This shows how to use the custom errors package
//
import (
	"strconv"
	"testing"
)

func atoi() (int, error) {
	i, err := strconv.Atoi("f42")
	if err != nil {
		return 0, Wrap(err)
	}
	return i, nil
}

// run this as;
//
//	go test -v ./...
func TestWrap(t *testing.T) {
	_, err := atoi()
	if err != nil {
		t.Log(err)
	}
}
