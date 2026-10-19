package handler

import (
	"encoding/json"
	"testing"
	"time"

	"example.com/go-clean/internal/usecase"
)

func TestNewUserResponse_CreatedAt(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name string
		now  time.Time
		want string
	}{
		{
			name: "ナノ秒を切り捨て",
			now:  time.Date(2026, time.January, 1, 0, 0, 0, 123456789, time.UTC),
			want: "2026-01-01T00:00:00.123456Z",
		},
		{
			name: "秒の繰り上げなし",
			now:  time.Date(2026, time.January, 1, 0, 0, 0, 999999999, time.UTC),
			want: "2026-01-01T00:00:00.999999Z",
		},
		{
			name: "UTCに統一",
			now:  time.Date(2026, time.January, 1, 9, 0, 0, 123456000, time.FixedZone("JST", 9*60*60)),
			want: "2026-01-01T00:00:00.123456Z",
		},
		{name: "小数部なし", now: time.Date(2026, time.January, 1, 0, 0, 0, 0, time.UTC), want: "2026-01-01T00:00:00Z"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Parallel()

			created := newUserResponse(
				&usecase.UserOutput{ID: "user-id", Name: "Taro", Email: "taro@example.com", CreatedAt: tt.now},
			)
			if got := created.CreatedAt.Format(time.RFC3339Nano); got != tt.want {
				t.Fatalf("created_at = %q, want %q", got, tt.want)
			}

			// PostgreSQL/pgxでマイクロ秒精度になった日時から、取得応答を作る。
			persisted := newUserResponse(
				&usecase.UserOutput{
					ID:        "user-id",
					Name:      "Taro",
					Email:     "taro@example.com",
					CreatedAt: time.UnixMicro(tt.now.UnixMicro()).UTC(),
				},
			)

			createJSON, err := json.Marshal(created)
			if err != nil {
				t.Fatal(err)
			}

			getJSON, err := json.Marshal(persisted)
			if err != nil {
				t.Fatal(err)
			}

			if string(createJSON) != string(getJSON) {
				t.Fatalf("create = %s, get = %s", createJSON, getJSON)
			}
		})
	}
}
