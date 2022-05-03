// Package errors provides ability to annotate you regular Go errors with stack traces.
//
// To use this package, you could replace this code;
//
//     if err != nil {
//         return err
//     }
//
// with;
//
//     if err != nil {
//         return errors.Wrap(err)
//     }
//
package errors

import (
	"fmt"
	"runtime"
	"strings"
)

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
			trace = trace + fmt.Sprintf("\n\tFile: %s, Line: %d. Function: %s", frame.File, frame.Line, frame.Function)
		}
		if !more {
			break
		}
	}
	return trace
}
