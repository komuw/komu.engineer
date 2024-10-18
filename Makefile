check:
	@curl -kLI "https://localhost:65081/cv/komu-CV.pdf"
	@curl -kLI "https://localhost:65081/"
	@curl -kLI "https://localhost:65081/blogs/12/propagate-context-without-cancellation.html"
	@curl -kLI "https://localhost:65081/blogs/12/propagate-context-without-cancellation"
	@curl -kLI "https://localhost:65081/blogs/go-gc-maps"
