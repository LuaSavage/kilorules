## Unit Testing Rules for Go

## Required Imports
always use these custom dependencies instead of standard ones:
```go
import (
    "stash.sigma.sbrf.ru/smark/tagme-taskflow/pkg/util/testify/require"
    "stash.sigma.sbrf.ru/smark/tagme-taskflow/pkg/util/testify/assert"
    "stash.sigma.sbrf.ru/sdvoice/gommon/pkg/errors"
)
```

## Mock Generation

### Use mockery for mock generation. Add to the test file:
```go
//go:generate mockery --name=Repository --inpackage --structname=mockRepository
```
**Important**: Only add this line if the mock for this interface hasn't been generated in the current package yet.

## Test Structure

### Table-Driven Tests

All unit tests must be table-driven tests. Follow this structure:

```go
func TestFunctionName(t *testing.T) {
    tests := []struct {
        name        string
        // Test parameters matching the function signature
        inputParam1 string
        inputParam2 int

        // Authentication context
        user *auth.User
        
        // Mock calls expectations
        repositoryCalls *repositoryCalls
        
        // Expected results
        wantResult      interface{}
        wantErr         error
        wantAPIResponse *response.Response[boilerplate.AddBonusResponse]
        wantAPIErr      response.APIError
    }{
        // Test cases here
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Test implementation
        })
    }
}
```

### Test Case Naming Convention

- Positive scenarios: Start with OK, {details}

 - Example: OK, valid request with all parameters
 - Example: OK, empty list returns zero results

- Negative scenarios: Start with Error with {methodname}

 - Example: Error with GetMarkersStats, database connection failed
 - Example: Error with ValidateInput, invalid parameter

### Mock Call Structure
**Important:** use `m.EXPECT()`. instead of `m.ON().`
Define mock call structures following this pattern:

```go
// Define call structures for each mocked method
type getMarkersStatsCall struct {
    // Input parameters
    markerIDs []uuid.UUID
    statAt    time.Time
    
    // Expected returns
    receivedMarkerStats []db.MarkerStat
    receivedErr         error
}

type getMarkerSkillLevelWithModificationsByPeriodCall struct {
    // Input parameters
    startPeriod time.Time
    endPeriod   time.Time
    
    // Expected returns
    receivedMarkerSkillLevelWithModifications []db.GetMarkerSkillLevelWithModificationsByPeriodRow
    receivedErr                               error
}

// Aggregate all calls
type repositoryCalls struct {
    getMarkersStats                              []getMarkersStatsCall
    getMarkerSkillLevelWithModificationsByPeriod []getMarkerSkillLevelWithModificationsByPeriodCall
}

// Mock factory function
func makeRepositoryMock(t *testing.T, call *repositoryCalls) *mockRepository {
    t.Helper()
    m := newMockRepository(t)
    
    if call != nil {
        for _, methodCall := range call.getMarkersStats {
            m.EXPECT().GetMarkersStats(anyCtx, methodCall.markerIDs, methodCall.statAt).
                Return(methodCall.receivedMarkerStats, methodCall.receivedErr).Once()
        }
        for _, methodCall := range call.getMarkerSkillLevelWithModificationsByPeriod {
            m.EXPECT().GetMarkerSkillLevelWithModificationsByPeriod(anyCtx, methodCall.startPeriod, methodCall.endPeriod).
                Return(methodCall.receivedMarkerSkillLevelWithModifications, methodCall.receivedErr).Once()
        }
    }
    
    return m
}

// Global mock matchers (add if not present in package)
var (
    anyCtx = mock.Anything
    anyTx  = mock.Anything
)
```
## Test Implementation Pattern

### Authentication Context Handling
When testing functions that require authentication:

```go
func TestHandler(t *testing.T) {
    tests := []struct {
        name    string
        user    *auth.User  // Define user in test case
        // ... other fields
    }{
        {

        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            // Set up some context with user if provided
            ctx := context.Background()
            if tt.user != nil {
                ctx = auth.SetRequestUser(ctx, tt.user)
            }
            
            // Test implementation
            // ...
        })
    }
}
```

## Helpers and testcase code order
First write that very test code  
Then, at file footer write helper code if it's really necessary  
Move anyCtx and other any vars to top, if they're necessary  



