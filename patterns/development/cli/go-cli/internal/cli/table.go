package cli

import (
	"fmt"
	"io"
	"strings"
	"text/tabwriter"
)

// WriteTable が使う tabwriter の設定値を定義する。
const (
	tableMinWidth = 0
	tableTabWidth = 8
	tablePadding  = 2
)

// WriteTable は header と rows を空白で列がそろう表として書き出す。
// コマンドで複数件を文章で一覧表示するときはこの関数を使う。
func WriteTable(w io.Writer, header []string, rows [][]string) error {
	tw := tabwriter.NewWriter(w, tableMinWidth, tableTabWidth, tablePadding, ' ', 0)
	_, err := io.WriteString(tw, strings.Join(header, "\t")+"\n")
	if err != nil {
		return err
	}
	for _, row := range rows {
		_, err = io.WriteString(tw, strings.Join(row, "\t")+"\n")
		if err != nil {
			return err
		}
	}
	err = tw.Flush()
	if err != nil {
		return fmt.Errorf("flush table: %w", err)
	}
	return nil
}
