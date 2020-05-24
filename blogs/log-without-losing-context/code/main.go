package main

import (
	"errors"
	"io"
	"io/ioutil"
	"math/rand"
	"os"
	"time"

	"github.com/sirupsen/logrus"
)

/*
run as:
  go run -race .
*/

func main() {
	// send logs to nowhere by default
	logrus.SetOutput(ioutil.Discard)
	logrus.SetFormatter(&logrus.JSONFormatter{})

	// Use our custom hook that will append logs to a circular buffer
	// and ONLY flush them to stderr when errors occur.
	logrus.AddHook(&hook{writer: os.Stderr})

	updateSocialMedia("Sending out my first social media status message")
}

func updateSocialMedia(msg string) {
	traceID := "sa225Hqk" //should be randomly generated per call
	logger := logrus.WithFields(logrus.Fields{"traceID": traceID})

	tweet(msg, logger)
	facebook(msg, logger)
	linkedin(msg, logger)
}

func tweet(msg string, logger *logrus.Entry) {
	logger.Info("tweet send start")
	// code to call twitter API goes here
	logger.Info("tweet send end.")
}

func facebook(msg string, logger *logrus.Entry) {
	logger.Info("facebook send start")
	err := facebookAPI(msg)
	if err != nil {
		logger.Errorf("facebook send failed. error=%s", err)
	}
	logger.Info("facebook send end.")
}

func linkedin(msg string, logger *logrus.Entry) {
	logger.Info("linkedin send start")
	// code to call linkedin API goes here
	logger.Info("linkedin send end.")
}

func facebookAPI(msg string) error {
	// fake code to call facebook API
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	if r.Intn(10) > 6 {
		// simulate an error occuring
		return errors.New("http 500")
	}
	return nil
}

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
