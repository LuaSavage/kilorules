# Fixture Type Inference in Pytest

## Context
When writing pytest test cases, accurately typing forwarded fixtures improves code clarity, IDE support, and static analysis. This guide provides rules for determining the correct type annotations.

## Core Rule
**Always annotate fixture parameters in test functions** with their precise type. Use this decision flow:

1. **Primary Source**: Use the fixture's return type annotation from its definition.
2. **Fallback**: If fixture lacks annotation, infer from:
   - Lookup from Type Reference Table
   - The fixture's dependencies and their types
   - How the fixture value is used in existing tests
   - Project patterns for similar fixtures
4. **Last Resort**: Use `Any` only as temporary

## Type Reference Table
Use this table for common fixture patterns in our codebase:

| Parameter | Types |
|-----------|-------|
| `_jobs_taskflow_config_archive` | `Dict[str, Any]` |
| `admin` | `Admin` |
| `bonuses_statistics_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `bucket_provider` | `BucketProvider` |
| `create_markup_task` | `Callable[..., Awaitable[MarkupTask]], tp.Callable, tp.Callable[..., tp.Any], tp.Callable[..., tp.Awaitable[MarkupTask]]` |
| `create_task_and_assign_markers_factory` | `tp.Callable[..., tp.Awaitable[tp.Tuple[tp.List[MarkupTask], MarkupProject]]]` |
| `customers` | `tp.List[Customer]` |
| `exam_task_data` | `tp.Dict[str, tp.Any]` |
| `favourite_project_and_task` | `tp.Tuple` |
| `item_consistency_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `jobs_taskflow_config` | `Dict[str, Any], tp.Dict[str, tp.Any]` |
| `make_task_available_for_markers` | `tp.Callable, tp.Callable[..., None]` |
| `markers` | `tp.List[Marker]` |
| `markup_events_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `markup_exam_task` | `MarkupTask` |
| `markup_prod_task` | `MarkupTask` |
| `markup_prod_task_with_honeypots_small` | `Any, MarkupTask` |
| `markup_results_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `markup_task_prod` | `MarkupTask` |
| `multiple_projects` | `tp.Callable[..., tp.Awaitable[tp.List[tp.Tuple[tp.List[MarkupTask], MarkupProject]]]]` |
| `new_marker` | `Marker` |
| `organization_admin` | `OrganizationAdmin` |
| `pg_conn` | `connection` |
| `pg_cur` | `cursor` |
| `pool_with_markers` | `Pool` |
| `project` | `MarkupProject, Project` |
| `project_for_markup` | `tp.Tuple` |
| `project_stats_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `retry_task_data` | `tp.Dict` |
| `service_token` | `tp.Callable` |
| `set_marker_skill_via_exam` | `tp.Callable` |
| `skills` | `tp.List[Skill]` |
| `stat_user` | `StatUser` |
| `study_task_data` | `tp.Dict, tp.Dict[str, tp.Any]` |
| `task` | `MarkupTask` |
| `task_archived_by_taskflow_jobs` | `MarkupTask` |
| `task_cc_res_3_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `task_consistency_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `task_creator` | `TaskCreator` |
| `task_data` | `Dict[str, Any], dict, tp.Dict, tp.Dict[str, tp.Any]` |
| `task_loading_config` | `tp.Dict` |
| `task_stats_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `taskflow_client` | `TaskflowClient` |
| `tasks_to_archive` | `MarkupTask` |
| `user_skills_consumer` | `tp.Tuple[KafkaConsumer, tp.List[TopicPartition]]` |
| `user_token_generator` | `tp.Callable, tp.Callable[[str], str]` |
| `user_with_role` | `tp.Union[OrganizationAdmin, Customer]` |
