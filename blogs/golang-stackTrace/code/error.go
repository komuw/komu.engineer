package main

import (
	"fmt"
	"runtime"
	"strconv"
	"strings"
)

/*
API for an errors package that provides stack traces.
*/

type Error struct {
	Stack      []uintptr
	StackTrace string
	Err        error
}

func (m Error) Error() string {
	return m.Err.Error() + m.StackTrace
}

func newError(err error) Error {
	stack := make([]uintptr, 50)
	length := runtime.Callers(2, stack[:])
	mStack := stack[:length]
	myt := Error{Stack: mStack, StackTrace: getStackTrace(mStack), Err: err}
	return myt
}

func getStackTrace(stack []uintptr) string {
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
		return 0, newError(err)
	}
	return i, nil

}

func main() {
	_, err := error1()
	if err != nil {
		fmt.Println(err)
	}

}
