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
	Writer      io.Writer
	entrybuffer [][]byte
}

// TODO: docs
func (h *hook) Fire(entry *logrus.Entry) error {
	line, err1 := entry.Bytes()
	if err1 != nil {
		return err1
	}
	h.entrybuffer = append(h.entrybuffer, line)

	if entry.Level <= logrus.ErrorLevel {
		var err2 error
		for _, line := range h.entrybuffer {
			_, err2 = h.Writer.Write(line)
		}
		h.entrybuffer = nil //clear the slice
		return err2
	}

	return nil //TODO: remove this
}

// Levels define on which log levels this hook would trigger
func (h *hook) Levels() []logrus.Level {
	return logrus.AllLevels
}

func main() {
	logrus.SetOutput(ioutil.Discard) // Send all logs to nowhere by default
	logrus.SetFormatter(&logrus.JSONFormatter{})

	logrus.AddHook(&hook{ // Send logs with level higher than warning to stderr
		Writer: os.Stderr,
	})

	logrus.Info("Info message 1.")
	logrus.Warn("Warn message 1.")
	logrus.Error("Error message 1.")
}
