package repository

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log/slog"

	"example.com/go-clean/internal/usecase"
)

var _ usecase.TxManager = (*TxManager)(nil)

// TxManager は usecase.TxManager の database/sql 実装。
type TxManager struct {
	db *sql.DB
}

// NewTxManager は TxManager を生成する。
func NewTxManager(db *sql.DB) *TxManager {
	return &TxManager{db: db}
}

// Do は fn をトランザクション内で実行する。既にトランザクション中なら合流する。
func (m *TxManager) Do(ctx context.Context, fn func(ctx context.Context) error) (err error) {
	if _, ok := ctx.Value(txKey{}).(*sql.Tx); ok {
		return fn(ctx)
	}

	tx, err := m.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}

	defer func() {
		if p := recover(); p != nil {
			if rbErr := tx.Rollback(); rbErr != nil {
				slog.ErrorContext(ctx, "rollback after panic", "error", rbErr)
			}

			panic(p)
		}

		if err == nil {
			return
		}

		if rbErr := tx.Rollback(); rbErr != nil {
			err = errors.Join(err, fmt.Errorf("rollback: %w", rbErr))
		}
	}()

	if err = fn(context.WithValue(ctx, txKey{}, tx)); err != nil {
		return err
	}

	if err = tx.Commit(); err != nil {
		return fmt.Errorf("commit: %w", err)
	}

	return nil
}
