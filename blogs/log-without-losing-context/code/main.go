package main

import (
	"errors"
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
	traceID := "sa225Hqk" // should be randomly generated per call
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
