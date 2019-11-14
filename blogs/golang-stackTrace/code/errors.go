package main

import (
	"errors"
	"fmt"
	"runtime"
	"strconv"
	"strings"
)

/*
API for an errors package that provides stack traces.
*/

const maxStackLength = 50

// Error is the type that implements the error interface.
// It contains the underlying err and the stacktrace of the error site..
type Error struct {
	Err        error
	StackTrace string
}

func (m Error) Error() string {
	return m.Err.Error() + m.StackTrace
}

// Wrap annotates the given error with a stack trace
func Wrap(err error) Error {

	return Error{StackTrace: getStackTrace(), Err: err}
}

func getStackTrace() string {
	stackBuf := make([]uintptr, maxStackLength)
	length := runtime.Callers(3, stackBuf[:])
	stack := stackBuf[:length]

	trace := ""
	frames := runtime.CallersFrames(stack)
	for {
		frame, more := frames.Next()
		if !strings.Contains(frame.File, "runtime/") {
			trace = trace + fmt.Sprintf("\n\tFile: %s, Line: %d. Function: %s.", frame.File, frame.Line, frame.Function)
		}
		if !more {
			break
		}
	}
	return trace
}

/*
how to use that API
*/
func error1() (int, error) {
	i, err := strconv.Atoi("f42")
	if err != nil {
		return 0, Wrap(err)
	}
	return i, nil

}

func main() {
	_, err := error1()
	if err != nil {
		fmt.Println(err)
	}

	e := errors.New("something bad happened")
	fmt.Println()
	fmt.Println(Wrap(e))

}
