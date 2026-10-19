package main

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"example.com/go-clean/internal/adapter/handler"
	"example.com/go-clean/internal/adapter/repository"
	"example.com/go-clean/internal/infra/config"
	"example.com/go-clean/internal/infra/database"
	"example.com/go-clean/internal/infra/logger"
	"example.com/go-clean/internal/usecase"
)

const (
	readHeaderTimeout = 5 * time.Second
	readTimeout       = 10 * time.Second
	writeTimeout      = 10 * time.Second
	idleTimeout       = 60 * time.Second
	shutdownTimeout   = 10 * time.Second
)

func main() {
	if err := run(); err != nil {
		slog.Error("server exited", "error", err)
		os.Exit(1)
	}
}

func run() error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	cfg, err := config.Load()
	if err != nil {
		return err
	}

	slog.SetDefault(logger.New(cfg.LogLevel))

	db, err := database.Open(ctx, cfg.DatabaseURL)
	if err != nil {
		return err
	}
	defer db.Close()

	// --- DI: 依存の組み立てはここだけで行う ---
	txManager := repository.NewTxManager(db)
	userRepo := repository.NewUserRepository(db)
	userHandler := handler.NewUserHandler(usecase.NewUserUsecase(userRepo, txManager))

	srv := &http.Server{
		Addr:              cfg.Addr,
		Handler:           handler.NewRouter(userHandler),
		ReadHeaderTimeout: readHeaderTimeout,
		ReadTimeout:       readTimeout,
		WriteTimeout:      writeTimeout,
		IdleTimeout:       idleTimeout,
	}

	errCh := make(chan error, 1)

	go func() {
		slog.Info("server started", "addr", cfg.Addr)

		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}

		close(errCh)
	}()

	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
	}

	slog.Info("shutting down")

	shutdownCtx, cancel := context.WithTimeout(context.Background(), shutdownTimeout)
	defer cancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		return fmt.Errorf("shutdown server: %w", err)
	}

	return nil
}
