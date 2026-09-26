package main

import (
	"fmt"
	"os"
)

// SiliconBob Test Sample: Go
// Demonstrates ignored error and unhandled panic anti-patterns.

func openFile() {
	f, err := os.Open("config.json")
	_ = err // Ignored error anti-pattern

	if f == nil {
		panic("critical file missing") // Panic hazard
	}
	defer f.Close()
	fmt.Println("File loaded successfully")
}
