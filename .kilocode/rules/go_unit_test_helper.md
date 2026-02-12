## Unit Testing Rules for Go

### Mockery Code Generation Pattern

We use a custom code generation tool `go-mockery-descriptor` that creates type-safe mock call tracking structures.

#### 1. Generation Directive
Place this in the interface definition file:
```go
//go:generate go-mockery-descriptor
```

### 2. Descriptor Configuration

Create `.mockery-descriptor.yaml` in the same package directory:

```yaml
interfaces:
  - name: UserService
    rename-returns:
      GetUser.r0: User
      ListUsers.r0: Users
      # For methods returning only error
      CreateUser.r0: CreatedUserID  # or just omit if not needed
```

**CRITICAL RULES** for rename-returns:

❌ NEVER use auto-generated names (R0, R1, R2) - always rename!  
✅ Always check the actual implementation to find meaningful return names  
✅ Use singular/plural consistently with domain concepts  
✅ For methods returning only error, you can omit rename if the return isn't captured. 

### 3. Generated Pattern Structure

The tool generates this structure (DO NOT modify manually):

```go
type getUserCall struct {
    Id string
    
    ReceivedUser *User  // Renamed from R0
    ReceivedErr  error
}

type userServiceCalls struct {
    GetUser    []getUserCall
    ListUsers  []listUsersCall
    CreateUser []createUserCall
}

func makeUserServiceMock(t *testing.T, calls *userServiceCalls) UserService {
    t.Helper()
    m := newMockUserService(t)
    anyCtx := mock.Anything
    
    for _, call := range calls.GetUser {
        m.EXPECT().GetUser(anyCtx, call.Id).
            Return(call.ReceivedUser, call.ReceivedErr).
            Once()
    }
    // ... other methods
}
```

### 4. Best Practices

**DO:**  
✅ Place .mockery-descriptor.yaml next to the interface definition. 
✅ Use meaningful return names based on domain language. 
✅ Include only interfaces that need mocks in the config. 
✅ Commit generated mock files to version control. 
✅ Use t.Helper() in make functions for better test failure traces. 

**DON'T:**. 
❌ Never manually edit generated call structs  
❌ Don't use R0, R1 names in tests - always use renamed fields. 
❌ Don't generate mocks for interfaces without rename-returns. 
❌ Don't put multiple unrelated interfaces in one descriptor file. 

### 5. Finding Return Names

To find proper return names:  

Find the interface implementation. 
Check the method signature in the implementation. 
Look at the actual return variable names in the implementation. 
If implementation uses unnamed returns, check the interface documentation. 
As last resort - use the domain entity name (singular/plural). 

```go
// Implementation shows meaningful return names
func (s *userService) GetUser(ctx context.Context, id string) (*User, error) {
    // Return names from implementation: user, err
    return &User{}, nil  // Use "User" as return name
}
```
