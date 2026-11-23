package db

import (
	"context"
	"database/sql"
	"database/sql/driver"
	"regexp"
	"strings"

	"github.com/jackc/pgx/v5/stdlib"
)

type rewriteDriver struct{ base driver.Driver }
type rewriteConn struct{ driver.Conn }

func init() { sql.Register("hub-pgx", rewriteDriver{base: stdlib.GetDefaultDriver()}) }
func (d rewriteDriver) Open(name string) (driver.Conn, error) {
	c, err := d.base.Open(name)
	if err != nil {
		return nil, err
	}
	return rewriteConn{Conn: c}, nil
}

var ignoreInsert = regexp.MustCompile(`(?i)INSERT\s+OR\s+IGNORE\s+INTO`)
var nullSafeNot = regexp.MustCompile(`(?i)\bIS\s+NOT\s+(\$[0-9]+)`)
var sqliteRowID = regexp.MustCompile(`(?i)\browid\b`)

func pgSQL(q string) string {
	ignored := ignoreInsert.MatchString(q)
	q = ignoreInsert.ReplaceAllString(q, "INSERT INTO")
	q = sqliteRowID.ReplaceAllString(q, "ctid")
	var out strings.Builder
	quote := byte(0)
	n := 0
	for i := 0; i < len(q); i++ {
		c := q[i]
		if quote != 0 {
			out.WriteByte(c)
			if c == quote {
				if i+1 < len(q) && q[i+1] == quote {
					i++
					out.WriteByte(q[i])
				} else {
					quote = 0
				}
			}
			continue
		}
		if c == '\'' || c == '"' {
			quote = c
			out.WriteByte(c)
			continue
		}
		if c == '?' {
			n++
			out.WriteByte('$')
			out.WriteString(itoa(n))
			continue
		}
		out.WriteByte(c)
	}
	rendered := nullSafeNot.ReplaceAllString(out.String(), "IS DISTINCT FROM $1")
	if ignored {
		rendered += " ON CONFLICT DO NOTHING"
	}
	return rendered
}

func (c rewriteConn) Prepare(q string) (driver.Stmt, error) { return c.Conn.Prepare(pgSQL(q)) }
func (c rewriteConn) PrepareContext(ctx context.Context, q string) (driver.Stmt, error) {
	if v, ok := c.Conn.(driver.ConnPrepareContext); ok {
		return v.PrepareContext(ctx, pgSQL(q))
	}
	return c.Conn.Prepare(pgSQL(q))
}
func (c rewriteConn) ExecContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Result, error) {
	if v, ok := c.Conn.(driver.ExecerContext); ok {
		return v.ExecContext(ctx, pgSQL(q), args)
	}
	return nil, driver.ErrSkip
}
func (c rewriteConn) QueryContext(ctx context.Context, q string, args []driver.NamedValue) (driver.Rows, error) {
	if v, ok := c.Conn.(driver.QueryerContext); ok {
		return v.QueryContext(ctx, pgSQL(q), args)
	}
	return nil, driver.ErrSkip
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	return string(buf[i:])
}
