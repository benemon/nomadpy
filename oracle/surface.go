package main

import (
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"os"
	"path/filepath"
	"reflect"
	"slices"
	"sort"
	"strings"
)

type Surface struct {
	Module  string          `json:"module"`
	Version string          `json:"version"`
	Files   map[string]File `json:"files"`
}

type File struct {
	Methods []Method          `json:"methods"`
	Structs map[string]Struct `json:"structs"`
	Consts  []Const           `json:"consts"`
	// Types are the exported non-struct type declarations and their underlying types (CSISecrets: map[string]string).
	Types map[string]string `json:"types"`
}

type Method struct {
	Receiver string   `json:"receiver"`
	Name     string   `json:"name"`
	Params   []string `json:"params"`
	Results  []string `json:"results"`
}

type Struct struct {
	Fields []Field `json:"fields"`
}

type Field struct {
	Name      string `json:"name"`
	JSON      string `json:"json"`
	Type      string `json:"type"`
	Embedded  bool   `json:"embedded,omitempty"`
	OmitEmpty bool   `json:"omitempty,omitempty"`
}

type Const struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

func surface() (any, error) {
	m, err := pinnedModule()
	if err != nil {
		return nil, err
	}
	fset := token.NewFileSet()
	pkgs, err := parser.ParseDir(fset, m.Dir, func(fi os.FileInfo) bool {
		return !strings.HasSuffix(fi.Name(), "_test.go")
	}, 0)
	if err != nil {
		return nil, err
	}
	s := Surface{Module: module, Version: m.Version, Files: map[string]File{}}
	for path, f := range pkgs["api"].Files {
		s.Files[filepath.Base(path)] = fileSurface(f)
	}
	return s, nil
}

func fileSurface(f *ast.File) File {
	out := File{Methods: []Method{}, Structs: map[string]Struct{}, Consts: []Const{}, Types: map[string]string{}}
	for _, decl := range f.Decls {
		switch d := decl.(type) {
		case *ast.FuncDecl:
			if d.Recv == nil || !d.Name.IsExported() {
				continue
			}
			out.Methods = append(out.Methods, Method{
				Receiver: receiverName(d.Recv.List[0].Type),
				Name:     d.Name.Name,
				Params:   fieldTypes(d.Type.Params),
				Results:  fieldTypes(d.Type.Results),
			})
		case *ast.GenDecl:
			for _, spec := range d.Specs {
				switch sp := spec.(type) {
				case *ast.TypeSpec:
					st, ok := sp.Type.(*ast.StructType)
					if ok && sp.Name.IsExported() {
						out.Structs[sp.Name.Name] = structSurface(st)
					} else if !ok && sp.Name.IsExported() {
						out.Types[sp.Name.Name] = types.ExprString(sp.Type)
					}
				case *ast.ValueSpec:
					if d.Tok != token.CONST {
						continue
					}
					for i, name := range sp.Names {
						if !name.IsExported() {
							continue
						}
						value := ""
						if i < len(sp.Values) {
							value = types.ExprString(sp.Values[i])
						}
						out.Consts = append(out.Consts, Const{Name: name.Name, Value: value})
					}
				}
			}
		}
	}
	sort.Slice(out.Methods, func(i, j int) bool {
		if out.Methods[i].Receiver != out.Methods[j].Receiver {
			return out.Methods[i].Receiver < out.Methods[j].Receiver
		}
		return out.Methods[i].Name < out.Methods[j].Name
	})
	return out
}

func receiverName(expr ast.Expr) string {
	if star, ok := expr.(*ast.StarExpr); ok {
		expr = star.X
	}
	return types.ExprString(expr)
}

func fieldTypes(list *ast.FieldList) []string {
	out := []string{}
	if list == nil {
		return out
	}
	for _, f := range list.List {
		t := types.ExprString(f.Type)
		n := len(f.Names)
		if n == 0 {
			n = 1
		}
		for i := 0; i < n; i++ {
			out = append(out, t)
		}
	}
	return out
}

func structSurface(st *ast.StructType) Struct {
	out := Struct{Fields: []Field{}}
	for _, f := range st.Fields.List {
		t := types.ExprString(f.Type)
		tag := ""
		if f.Tag != nil {
			tag = reflect.StructTag(strings.Trim(f.Tag.Value, "`")).Get("json")
		}
		parts := strings.Split(tag, ",")
		jsonName := parts[0]
		if jsonName == "-" {
			continue
		}
		omitEmpty := slices.Contains(parts[1:], "omitempty")
		if len(f.Names) == 0 {
			name := strings.TrimPrefix(t, "*")
			out.Fields = append(out.Fields, Field{Name: name, JSON: jsonName, Type: t, Embedded: true})
			continue
		}
		for _, name := range f.Names {
			if !name.IsExported() {
				continue
			}
			j := jsonName
			if j == "" {
				j = name.Name
			}
			out.Fields = append(out.Fields, Field{Name: name.Name, JSON: j, Type: t, OmitEmpty: omitEmpty})
		}
	}
	return out
}
