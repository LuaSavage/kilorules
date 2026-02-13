# Rule: go-mockery-descriptor — Configuration and Usage

## Required: go:generate

**Once** add the directive to the test package (any `*_test.go` file), if not already present:

```go
//go:generate go-mockery-descriptor
```

Placement: in any `*_test.go` file of the package where the generated mock is used. Run: `go generate ./...` or `go generate ./path/to/package` from the module root.

---

## Filling `.mockery-descriptor.yaml`

Place the file in the package directory that contains the interface, or in the module root (search walks up to `go.mod`).

### Minimal structure

```yaml
interfaces:
  - name: InterfaceName
```

### Full example

```yaml
constructor-name: "newMock{{ . }}"
package-name: "{{ . }}"
output: "{{ . }}.gen_test.go"
interfaces:
  - name: UserService
    rename-returns:
      GetUser.r0: User
      GetUser.r1: Err
      ListUsers.r0: Users
    field-overwriter-param:
      - Save.items=elementsMatch
      - SetStatus.status=oneOf
      - Log.msg=any
```

### Interface-level fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Exact Go interface name |
| `rename-returns` | No | Rename return fields in call structs |
| `field-overwriter-param` | No | Override matchers for method parameters |

### rename-returns

Format: `Method.rN: NewName`, where `r0`, `r1` are return value indices.

- `r0` — first return, `r1` — second, etc.
- Without renaming you get `ReceivedR0`, `ReceivedR1`.
- For `error` use `Err` or leave default.

Examples:
```yaml
rename-returns:
  GetUser.r0: User      # (*User, error) → ReceivedUser
  GetUser.r1: Err       # error → ReceivedErr
  List.r0: Items        # []Item → ReceivedItems
  Create.r0: ID         # (string, error) → ReceivedID
```

### field-overwriter-param

Format: `Method.ParamName=matcher`

Supported matchers:

| Matcher | Purpose |
|---------|---------|
| `elementsMatch` | Slice: element order does not matter |
| `oneOf` | Value must be one of the expected values |
| `any` | Any value (mock.Anything) |

Examples:
```yaml
field-overwriter-param:
  - FindByIDs.ids=elementsMatch   # []string — order-independent
  - Update.status=oneOf           # enum-like — one of allowed values
  - LogMessage.ctx=any            # context — always any
  - Callback.fn=any               # callback — always any
```

### Global parameters (optional)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `constructor-name` | `newMock{{ . }}` | Mock constructor name template |
| `package-name` | `{{ . }}_test` | Package name in generated file |
| `output` | `{{ . }}.mockery-helper_test.go` | Output file name template |

`{{ . }}` is substituted with the interface name (constructor/output) or package name (package-name).

---

## Pre-add checklist

1. The interface is already defined in the package.
2. Mockery mock is already generated (`//go:generate mockery --name=X --inpackage --with-expecter=true --structname=mockX`).
3. Test package has `//go:generate go-mockery-descriptor` (if not — add once).
4. `.mockery-descriptor.yaml` is in the correct directory.
5. `name` in `interfaces` matches the interface name.
6. `rename-returns` and `field-overwriter-param` match method signatures.
