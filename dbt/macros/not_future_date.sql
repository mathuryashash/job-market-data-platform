-- Custom dbt test: no_future_dates
-- Usage in .yml: tests: - not_future_date
-- Fails if any non-null date is in the future (> current_date + 1 day tolerance).

{% test not_future_date(model, column_name) %}
select {{ column_name }}
from {{ model }}
where
    {{ column_name }} is not null
    and {{ column_name }} > current_date + interval '1 day'
{% endtest %}
