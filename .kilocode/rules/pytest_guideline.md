# Pytest Test Writing Standards

## Core Principles
- **Type Safety**: All test parameters and return values must be explicitly typed
- **Clarity**: Every assertion must be descriptive and self-documenting
- **Traceability**: Tests must be linked to requirements and provide clear execution traces

## 1. Type Annotations
```python
# ✅ Correct
async def test_create_task(
    task_service: TaskService,  # Explicit type
    test_user: UserModel        # Explicit type
) -> None:                      # Explicit return type
    # Test implementation

# ❌ Incorrect
async def test_create_task(task_service, test_user):
    # Missing type annotations
```
## 2. Assertion Standards
- Never use bare asserts: Every assertion must have a descriptive message
- **Capitalization**: All assertion messages and allure logs must start with capital letter
- **Language**: Use Russian for test descriptions and assertion messages, but keep English for:

--Project-specific terms
--Entity names
--Technical terminology
```python
# ✅ Correct
assert response.status == 200, "Статус код должен быть 200"
assert len(items) > 0, "Список должен содержать элементы"

# ❌ Incorrect
assert response.status == 200
assert len(items) > 0
```

## 3. Test Decorators Template
```python
@pytest.mark.asyncio
@allure.epic("api")
@allure.feature("Taskflow")
@allure.story(
    "https://jira.sberbank.ru/browse/TAGME-7650", "https://jira.sberbank.ru/browse/TAGME-9056", "TAGME-9056"
)
```
## 4. Logging Rules
- **Important:** Use allure_logs for commenting test flow instead of regular comments
- Apply @allure_step_decorator before functions where you want allure logs
- All allure logs must start with capital letter

```python
@allure_step_decorator
def setup_test_data() -> TestData:
    allure_logs("Создание тестовых данных для проверки таскфлоу")
    # Implementation

# ✅ Correct allure log
allure_logs("Проверяем создание новой задачи в системе")

# ❌ Incorrect  
allure_logs("проверяем создание задачи")  # Lowercase start
```

## 5. Taskflow Service Responses
### Complex Response Assertion Pattern

When using **taskflow.py** service methods that return non-dictionary types:

1.Create expected data class instance with predefined values
2.Compare entire response object against expected instance

```python
# ✅ Correct
@allure.story("TAGME-1234")
async def test_taskflow_operation(taskflow_client: TaskflowClient) -> None:
    # Act
    response = await taskflow_client.execute_operation()
    
    # Arrange expected result
    expected = TaskflowResult(
        id="test-id",
        status="completed",
        artifacts=["report.pdf"],
        metadata={"version": "1.0"}
    )
    
    # Assert
    assert response == expected, "Результат операции должен соответствовать ожиданиям"

# ❌ Incorrect
async def test_taskflow_operation(taskflow_client: TaskflowClient) -> None:
    response = await taskflow_client.execute_operation()
    
    # Fragmented assertions
    assert response.id == "test-id"
    assert response.status == "completed"
    assert "report.pdf" in response.artifacts
```

## 6. Variable Naming Conventions
### Preferred Naming Patterns
```
# ✅ Clear and specific
user_with_admin_role = create_user(role="admin")
task_execution_result = await run_task()
validation_error_messages = get_errors()

# ❌ Avoid "parasite" words
data = get_data()          # Too vague
info = process_info()      # Unclear content
manager = create_manager() # Ambiguous purpose
something = calculate()    # Meaningless
```
### Acceptable Exceptions
Loop variables: ```for item in items:```
Simple counters: ```index, count```
Well-established patterns: ```response, request, client```

## 7. Test Structure Template

```python
@pytest.mark.asyncio
@allure.epic("api")
@allure.feature("ModuleName")
@allure.story("JIRA_STORY_LINK", "JIRA_TASK_LINK", "JIRA_TASK_ID")
async def test_specific_functionality(
    fixture_with_type: FixtureType,
    another_fixture: AnotherType
) -> None:
    """Описание теста на русском языке с упоминанием English терминов."""
    
    # Setup
    allure_logs("Подготовка тестовых данных")
    test_data = prepare_test_data()
    
    # Action
    allure_logs("Выполнение тестируемой операции")
    result = await execute_operation(test_data)
    
    # Expected result
    expected = ExpectedResult(
        field1="value1",
        field2="value2"
    )
    
    # Assertion
    assert result == expected, "Детальное описание проверки на русском"
    
    # Additional verification if needed
    if has_additional_checks:
        allure_logs("Проверка дополнительных условий")
        assert condition, "Сообщение об ошибке"
```

## 8. Pytest parametrization
## use @pytest.mark.parametrize instead of several similar tests
```python
# ❌ BAD: Code repetition
def test_small_file():
    result = process_file("small.txt")
    assert result.success

def test_medium_file():
    result = process_file("medium.txt") 
    assert result.success

# ✅ GOOD: Parameterization
@pytest.mark.parametrize("file_name,expected_size", [
    ("small.txt", 1024),
    ("medium.txt", 10240),
    ("large.txt", 102400),
])
def test_file_processing(file_name: str, expected_size: int):
    """Тестирование обработки файлов разных размеров."""
    result = process_file(file_name)
    assert result.size == expected_size
```

## 9. Enum Pattern for String Constants
```python
# ❌ BAD: Hardcoded string comparisons
if status == "pending":
    handle_pending()
elif status == "completed":
    handle_completed()

# ✅ GOOD: Use enums
class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    
if status == TaskStatus.PENDING:
    handle_pending()
elif status == TaskStatus.COMPLETED:
    handle_completed()
```

## Checklist Before Finalizing Test

- All parameters and return values have type hints
- Every assertion has descriptive text in Russian (capitalized)
- Allure steps used instead of regular comments
- Variables have clear, specific names
- String constants replaced with enums where repetitive
- Code duplication eliminated via parameterization or loops
- Test header follows the exact template
- Complex responses validated against dataclass instances
- Dont left unused variables
