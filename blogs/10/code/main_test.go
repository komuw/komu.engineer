package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"testing"
	"time"
)

//////////////////////////////////////////////// implementation ////////////////////////////////////////////////
func logg(w io.Writer, msg string) error {
	msg = msg + "\n"
	_, err := w.Write([]byte(msg))
	return err
}

type httpLogger struct{}

func (h httpLogger) Write(p []byte) (n int, err error) {
	tr := &http.Transport{
		MaxIdleConns:       10,
		IdleConnTimeout:    10 * time.Second,
		DisableCompression: true,
	}
	maxOfThreeRedirects := func(req *http.Request, via []*http.Request) error {
		max := 3
		if req.Header.Get("Auth") != "" {
			// requests that have set Auth header can follow more redirects.
			max = 12
		}
		if len(via) >= max {
			return fmt.Errorf("stopped after %d redirects", max)
		}
		return nil
	}
	client := &http.Client{
		Transport:     tr,
		Timeout:       10 * time.Second,
		CheckRedirect: maxOfThreeRedirects,
	}
	resp, err := client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))
	if err != nil {
		return 0, err
	}

	return int(resp.Request.ContentLength), nil
}

func main() {
	err := logg(os.Stdout, "hey-Stdout")
	if err != nil {
		log.Fatal(err)
	}
	err = logg(httpLogger{}, "hey-httpLogger")
	if err != nil {
		log.Fatal(err)
	}

	err = logg(&betterhttpLogger{}, "hey-betterhttpLogger")
	if err != nil {
		log.Fatal(err)
	}
}

//////////////////////////////////////////////// implementation ////////////////////////////////////////////////

///////////////////////////////////////////////////// test /////////////////////////////////////////////////////
func Test_logg(t *testing.T) {
	t.Run("mock", func(t *testing.T) {
		msg := "hey"
		mockWriter := &bytes.Buffer{}
		err := logg(mockWriter, msg)
		if err != nil {
			t.Fatalf("logg() got error = %v, wantErr = %v", err, nil)
			return
		}

		gotMsg := mockWriter.String()
		wantMsg := msg + "\n"
		if gotMsg != wantMsg {
			t.Fatalf("logg() got = %v, want = %v", gotMsg, wantMsg)
		}
	})

	t.Run("betterhttpLogger", func(t *testing.T) {
		msg := "hey"
		w := &betterhttpLogger{test: struct {
			enabled bool
			written string
		}{enabled: true}}
		err := logg(w, msg)
		if err != nil {
			t.Fatalf("logg() got error = %v, wantErr = %v", err, nil)
			return
		}

		gotMsg := w.test.written
		wantMsg := msg + "\n"
		if gotMsg != wantMsg {
			t.Fatalf("logg() got = %v, want = %v", gotMsg, wantMsg)
		}
	})
}

///////////////////////////////////////////////////// test /////////////////////////////////////////////////////

// With the above, the only thing you have tested is that `httpLogger` implements the `io.Writer` and that `bytes.Buffer` also implements the same.
// In other words, your tests have just duplicated the compile-time checks that Go is already giving you for free.
// The bulk of your application's implementation(the `Write`` method of `httpLogger` is wholly untested)

type betterhttpLogger struct {
	test struct {
		enabled bool
		written string
	}
}

func (h *betterhttpLogger) Write(p []byte) (n int, err error) {
	tr := &http.Transport{
		MaxIdleConns:       10,
		IdleConnTimeout:    10 * time.Second,
		DisableCompression: true,
	}
	maxOfThreeRedirects := func(req *http.Request, via []*http.Request) error {
		max := 3
		if req.Header.Get("Auth") != "" {
			// requests that have set Auth header can follow more redirects.
			max = 12
		}
		if len(via) >= max {
			return fmt.Errorf("stopped after %d redirects", max)
		}
		return nil
	}
	client := &http.Client{
		Transport:     tr,
		Timeout:       10 * time.Second,
		CheckRedirect: maxOfThreeRedirects,
	}
	if h.test.enabled {
		mockWriter := &bytes.Buffer{}
		n, err := mockWriter.Write(p)
		h.test.written = mockWriter.String()
		return n, err
	}
	resp, err := client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))
	return int(resp.Request.ContentLength), err
}

// In this version of the code, the only piece of code that is not tested ins just one line;
//    `client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))`
// And guess what? Since it is calling code from the standard library, you can bet[https://github.com/golang/go/blob/go1.18.1/src/net/http/client_test.go#L134-L142] that it is one of
// the most[https://github.com/golang/go/blob/go1.18.1/src/net/http/client_test.go#L606-L621] heavily tested functionality out there. So you don't have to re-test that which the Go team has/is already testing.
//
// If you have one interface implementation that you use in your 'real' application and another implementation that you use in tests; you are probably doing it wrong.
// You should, in my opinion, use just one interface implementation for both application and tests. The implementation should behave a bit different conditionally on whether you are running tests or not.
