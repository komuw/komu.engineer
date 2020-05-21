package main

import (
	"io"

	"github.com/sirupsen/logrus"
)

// hook to buffer logs and only send at right severity.
type hook struct {
	writer io.Writer

	// Note: in production, lineBuffer should use a circular buffer instead of a slice.
	// otherwise you may have unbounded memory growth.
	// we are just using a slice of []bytes here for brevity and blogging purposes.
	lineBuffer [][]byte
}

// Fire will append all logs to a circular buffer and only 'flush'
// them when a log of sufficient severity(ERROR) is emitted.
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

// Levels define on which log levels this hook would trigger
func (h *hook) Levels() []logrus.Level {
	return logrus.AllLevels
}
