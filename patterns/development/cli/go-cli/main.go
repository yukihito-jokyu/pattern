// Command go-cli は go-cli 基盤の見本となる CLI である。
//
// main はプロセスの引数・標準入出力・環境変数・時計を app.Run に渡し、返された終了コードで終了する。
package main

import (
	"context"
	"os"
	"os/signal"
	"time"

	"example.com/go-cli/internal/app"
)

// main は CLI を実行し、返された終了コードで終了する。
func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	code := app.Run(ctx, os.Args[1:], app.Env{
		Stdout: os.Stdout,
		Stderr: os.Stderr,
		Getenv: os.Getenv,
		Now:    time.Now,
	})
	stop()
	os.Exit(code)
}
