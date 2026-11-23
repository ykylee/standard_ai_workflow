package assets

import "embed"

//go:embed hub_client.py
var HubClientPy string

//go:embed standard_block.md
var StandardBlock string

//go:embed static/*
var StaticFS embed.FS
