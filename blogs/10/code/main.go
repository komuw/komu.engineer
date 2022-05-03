package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

// logg writes msg to the data stream provided by w
func logg(w io.Writer, msg string) error {
	msg = msg + "\n"
	_, err := w.Write([]byte(msg))
	return err
}

// httpLogger logs messages to a HTTP logging service
type httpLogger struct{}

// Write fulfills io.Writer interface
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
	return int(resp.Request.ContentLength), err
}

func main() {
	err := logg(httpLogger{}, "hey-httpLogger")
	if err != nil {
		log.Fatal(err)
	}
}

//
// type betterhttpLogger struct {
// 	test struct {
// 		enabled bool
// 		written string
// 	}
// }

// func (h *betterhttpLogger) Write(p []byte) (n int, err error) {
// 	tr := &http.Transport{
// 		MaxIdleConns:       10,
// 		IdleConnTimeout:    10 * time.Second,
// 		DisableCompression: true,
// 	}
// 	maxOfThreeRedirects := func(req *http.Request, via []*http.Request) error {
// 		max := 3
// 		if req.Header.Get("Auth") != "" {
// 			// requests that have set Auth header can follow more redirects.
// 			max = 12
// 		}
// 		if len(via) >= max {
// 			return fmt.Errorf("stopped after %d redirects", max)
// 		}
// 		return nil
// 	}
// 	client := &http.Client{
// 		Transport:     tr,
// 		Timeout:       10 * time.Second,
// 		CheckRedirect: maxOfThreeRedirects,
// 	}
// 	if h.test.enabled {
// 		mockWriter := &bytes.Buffer{}
// 		n, err := mockWriter.Write(p)
// 		h.test.written = mockWriter.String()
// 		return n, err
// 	}
// 	resp, err := client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))
// 	return int(resp.Request.ContentLength), err
// }

// In this version of the code, the only piece of code that is not tested ins just one line;
//    `client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))`
// And guess what? Since it is calling code from the standard library, you can bet[https://github.com/golang/go/blob/go1.18.1/src/net/http/client_test.go#L134-L142] that it is one of
// the most[https://github.com/golang/go/blob/go1.18.1/src/net/http/client_test.go#L606-L621] heavily tested functionality out there. So you don't have to re-test that which the Go team has/is already testing.
//
// If you have one interface implementation that you use in your 'real' application and another implementation that you use in tests; you are probably doing it wrong.
// You should, in my opinion, use just one interface implementation for both application and tests. The implementation should behave a bit different conditionally on whether you are running tests or not.
