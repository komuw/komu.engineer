package main

import (
	"bytes"
	"testing"
)

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

// With the above, the only thing you have tested is that `httpLogger` implements the `io.Writer` and that `bytes.Buffer` also implements the same.
// In other words, your tests have just duplicated the compile-time checks that Go is already giving you for free.
// The bulk of your application's implementation(the `Write`` method of `httpLogger` is wholly untested)
