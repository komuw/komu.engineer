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
