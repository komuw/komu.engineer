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

func updateSocial(msg string) {
	traceID := "sa225Hqk" //should be randomly generated
	logger := logrus.WithFields(logrus.Fields{"traceID": traceID})

	tweet(msg, logger)
	facebook(msg, logger)
	linkedin(msg, logger)
}

func tweet(msg string, logger *logrus.Entry) {
	logger.Info("tweet send start")
	logger.Info("tweet send end.")
}

func facebook(msg string, logger *logrus.Entry) {
	logger.Info("facebook send start")
	logger.Info("facebook send end.")
}

func linkedin(msg string, logger *logrus.Entry) {
	logger.Info("linkedin send start")
	err := linkedinAPI(msg)
	if err != nil {
		logger.Errorf("linkedin send failed. error=%s", err)
	}

	logger.Info("linkedin send end.")
}

func linkedinAPI(msg string) error {
	r := rand.New(rand.NewSource(time.Now().UnixNano()))
	if r.Intn(10) > 6 {
		// simulate an error occuring
		return errors.New("http 500")
	}
	return nil
}

func main() {
	// send logs to nowhere by default
	logrus.SetOutput(ioutil.Discard)
	logrus.SetFormatter(&logrus.JSONFormatter{})
	// use stderr for logs
	logrus.AddHook(&hook{writer: os.Stderr})

	updateSocial("Sending out my first social media message")
}
