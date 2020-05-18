package main

import (
	"io"
	"io/ioutil"
	"os"

	"github.com/sirupsen/logrus"
)

/*
run as:
  go run -race .
*/

// TODO: docs
type hook struct {
	writer io.Writer

	// Note: in production, lineBuffer should use a circular buffer instead of a slice.
	// we are just using a slice of []bytes here for brevity and blogging purposes.
	lineBuffer [][]byte
}

// TODO: docs
func (h *hook) Fire(entry *logrus.Entry) error {
	line, err1 := entry.Bytes()
	if err1 != nil {
		return err1
	}
	h.lineBuffer = append(h.lineBuffer, line)

	if entry.Level <= logrus.ErrorLevel {
		var err2 error
		for _, line := range h.lineBuffer {
			_, err2 = h.writer.Write(line)
		}
		h.lineBuffer = nil // clear the buffer
		return err2
	}

	return nil
}

// TODO: docs
func (h *hook) Levels() []logrus.Level {
	return logrus.AllLevels
}

func main() {
	// send logs to nowhere by default
	logrus.SetOutput(ioutil.Discard)
	logrus.SetFormatter(&logrus.JSONFormatter{})
	// use stderr for logs
	logrus.AddHook(&hook{writer: os.Stderr})

	logrus.Info("Info message 1.")
	logrus.Warn("Warn message 1.")
	logrus.Error("Error message 1.")

	logrus.Error("Error message 2.")
	logrus.Info("Info message 2.")

}
