package main

import (
	"encoding/json"
	"fmt"
	"os"
	"runtime"
	"time"
)

//  1. the python program gets a request from AWS lambda.
//  2. it serializes that request into json.
//  3. it writes that json into stdin
//  4. the Go program reads from stdin
//  5. it unmarshals what it has read from stdin and acts on it.
//  5. it creates a json marshaled response
//  6. it writes that json response to stdout
//  7. the python program reads that response from stdout
//  8. it unmarshals what it read(the response)
//  9. it sends the response back to AWS lambda.

// To run this programs:
// a. go build main.go
// b. python3 lambda.py

// To run this programs in AWS lambda(Python3.6):
// a. CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o main main.go
// b. zip mylambda.zip main lambda.py
// c. upload mylambda.zip to AWS lambda
// d. set Runtime to python3.6 and Handler to lambda.handle

// to test create an AWS test event that is just a string
// the default AWS test event looks like;
// {
// 	"key1": "value1",
// 	"key2": "value2",
// 	"key3": "value3"
//   }
// Do not use that since it does not match our Request struct.
// Use something like: "hey this is a test event."

type ErrResponse struct {
	Error string
}

type Request struct {
	Event   string `json:"event,omitempty"`
	Context string `json:"context,omitempty"`
}

type Response struct {
	EchoEvent   string `json:"echoevent,omitempty"`
	GOOS        string `json:"goos,omitempty"`
	GOARCH      string `json:"goarch,omitempty"`
	CurrentTime string `json:"currentTime,omitempty"`
}

func main() {
	/*
		We should remember to send a newline, so as to avoid deadlocks on the parent(python) process.
		That's why we use fmt.Println instead of fmt.Printf
	*/
	req := Request{}
	err := json.NewDecoder(os.Stdin).Decode(&req)
	if err != nil {
		errResponse := ErrResponse{Error: err.Error()}
		jsonErr, _ := json.Marshal(errResponse)
		fmt.Println(string(jsonErr))
	}

	t := time.Now()
	res := Response{EchoEvent: req.Event, GOOS: runtime.GOOS, GOARCH: runtime.GOARCH, CurrentTime: t.Format(time.UnixDate)}
	b, err := json.Marshal(res)
	if err != nil {
		errResponse := ErrResponse{Error: err.Error()}
		jsonErr, _ := json.Marshal(errResponse)
		fmt.Println(string(jsonErr))
	}
	fmt.Println(string(b))
}
