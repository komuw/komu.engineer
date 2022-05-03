package main

import (
	"bytes"
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
	client := &http.Client{
		Transport: tr,
		Timeout:   10 * time.Second,
	}
	// assume httpbin.org is an actual logging service.
	resp, err := client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))
	return int(resp.Request.ContentLength), err
}

func main() {
	err := logg(&betterhttpLogger{}, "hey-httpLogger")
	if err != nil {
		log.Fatal(err)
	}
}

// betterhttpLogger logs messages to a HTTP logging service
type betterhttpLogger struct {
	test struct {
		enabled bool
		written string
	}
}

// Write fulfills io.Writer interface
func (h *betterhttpLogger) Write(p []byte) (n int, err error) {
	tr := &http.Transport{
		MaxIdleConns:       10,
		IdleConnTimeout:    10 * time.Second,
		DisableCompression: true,
	}
	client := &http.Client{
		Transport: tr,
		Timeout:   10 * time.Second,
	}
	if h.test.enabled {
		mockWriter := &bytes.Buffer{}
		n, err := mockWriter.Write(p)
		h.test.written = mockWriter.String()
		return n, err
	}
	// assume httpbin.org is an actual logging service.
	resp, err := client.Post("https://httpbin.org/post", "application/json", bytes.NewReader(p))
	return int(resp.Request.ContentLength), err
}
