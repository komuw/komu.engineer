privateRepo:
	@export GOPRIVATE=github.com/komuw/srs && go get github.com/komuw/srs/ext@v0.0.1

run:
	@export KOMU_ENGINEER_WEBSITE_ENVIRONMENT="development"
	@export SRS_DB_PATH="/tmp/srs.sqlite"
	@goimports -w .;gofumpt -extra -w .;gofmt -w -s .;go mod tidy;go run -race github.com/komuw/komu.engineer 



check:
	@curl -kLI "https://localhost:65081/cv/komu-CV.pdf"
	@curl -kLI "https://localhost:65081/"
	@curl -kLI "https://localhost:65081/blogs/12/propagate-context-without-cancellation.html"
	@curl -kLI "https://localhost:65081/blogs/12/propagate-context-without-cancellation"
	@curl -kLI "https://localhost:65081/blogs/go-gc-maps"
